"""
高级使用示例

展示 SQLModel CRUD 模块的高级用法，包括：
- 自定义 CRUD 类
- 复杂查询和过滤
- 批量操作
- 事务处理
- 关联查询
"""

from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, select, Relationship

# 导入 CRUD 模块
from sqlmodel_crud import CRUDBase, DatabaseManager, NotFoundError, ValidationError

# =============================================================================
# 定义实体模型（带关系）
# =============================================================================


class Department(SQLModel, table=True):
    """部门实体模型"""

    __tablename__ = "departments"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(description="部门名称")
    code: str = Field(unique=True, description="部门编码")
    description: Optional[str] = Field(default=None, description="部门描述")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    # 关系
    employees: List["Employee"] = Relationship(back_populates="department")


class Employee(SQLModel, table=True):
    """员工实体模型"""

    __tablename__ = "employees"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(description="姓名")
    email: str = Field(unique=True, description="邮箱")
    phone: Optional[str] = Field(default=None, description="电话")
    salary: float = Field(default=0.0, description="薪资")
    is_active: bool = Field(default=True, description="是否在职")
    department_id: Optional[int] = Field(
        default=None, foreign_key="departments.id", description="部门ID"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    # 软删除字段
    is_deleted: bool = Field(default=False, description="是否已删除")
    deleted_at: Optional[datetime] = Field(default=None, description="删除时间")

    # 关系
    department: Optional[Department] = Relationship(back_populates="employees")


# =============================================================================
# 定义数据验证模型（用于创建和更新）
# =============================================================================


class DepartmentCreate(SQLModel):
    """部门创建模型"""

    name: str
    code: str
    description: Optional[str] = None


class DepartmentUpdate(SQLModel):
    """部门更新模型"""

    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None


class EmployeeCreate(SQLModel):
    """员工创建模型"""

    name: str
    email: str
    phone: Optional[str] = None
    salary: float = 0.0
    department_id: Optional[int] = None


class EmployeeUpdate(SQLModel):
    """员工更新模型"""

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    salary: Optional[float] = None
    is_active: Optional[bool] = None
    department_id: Optional[int] = None


# =============================================================================
# 自定义 CRUD 类
# =============================================================================


class DepartmentCRUD(CRUDBase[Department, DepartmentCreate, DepartmentUpdate]):
    """部门 CRUD 操作类

    展示如何使用独立的 Create/Update 模型。
    """

    def __init__(self):
        super().__init__(Department)

    def get_by_code(self, session, code: str) -> Optional[Department]:
        """根据编码查找部门"""
        statement = select(Department).where(Department.code == code)
        return session.execute(statement).scalars().first()

    def get_with_employees(self, session, department_id: int) -> Optional[Department]:
        """获取部门及其员工"""
        # 这里简化处理，实际可以使用 selectinload 等加载策略
        return self.get(session, department_id)


class EmployeeCRUD(CRUDBase[Employee, EmployeeCreate, EmployeeUpdate]):
    """员工 CRUD 操作类

    展示如何添加自定义查询方法。
    """

    def __init__(self):
        super().__init__(Employee)

    def get_by_email(self, session, email: str) -> Optional[Employee]:
        """根据邮箱查找员工"""
        statement = select(Employee).where(Employee.email == email)
        return session.execute(statement).scalars().first()

    def get_by_department(
        self, session, department_id: int, skip: int = 0, limit: int = 100
    ) -> List[Employee]:
        """获取部门下的员工"""
        return self.get_multi(
            session, skip=skip, limit=limit, filters={"department_id": department_id}
        )

    def get_active_employees(
        self,
        session,
        min_salary: Optional[float] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Employee]:
        """获取在职员工，可按最低薪资过滤"""
        # 基础过滤条件
        filters = {"is_active": True}

        # 获取结果
        employees = self.get_multi(
            session,
            skip=skip,
            limit=limit,
            filters=filters,
            order_by=[("salary", "desc")],
        )

        # 在内存中过滤薪资（实际应该在 SQL 中过滤）
        if min_salary is not None:
            employees = [e for e in employees if e.salary >= min_salary]

        return employees

    def get_high_earners(self, session, threshold: float = 10000.0) -> List[Employee]:
        """获取高薪员工"""
        statement = (
            select(Employee)
            .where(Employee.salary >= threshold)
            .order_by(Employee.salary.desc())
        )
        return list(session.execute(statement).scalars().all())

    def update_salary(self, session, employee_id: int, new_salary: float) -> Employee:
        """更新员工薪资（带验证）"""
        if new_salary < 0:
            raise ValidationError("薪资不能为负数", field="salary")

        return self.update(session, employee_id, {"salary": new_salary})

    def batch_update_department(
        self, session, employee_ids: List[int], new_department_id: int
    ) -> int:
        """批量更新员工部门

        Returns:
            更新的记录数
        """
        count = 0
        for emp_id in employee_ids:
            try:
                self.update(session, emp_id, {"department_id": new_department_id})
                count += 1
            except NotFoundError:
                # 跳过不存在的员工
                pass
        return count

    def get_with_deleted(self, session, employee_id: int) -> Optional[Employee]:
        """获取员工（包含已软删除的）

        用于恢复软删除员工时获取记录。

        Args:
            session: 数据库会话
            employee_id: 员工ID

        Returns:
            员工对象，不存在时返回 None
        """
        statement = select(Employee).where(Employee.id == employee_id)
        return session.execute(statement).scalars().first()

    def restore(self, session, employee_id: int) -> Employee:
        """恢复软删除的员工

        Args:
            session: 数据库会话
            employee_id: 要恢复的员工ID

        Returns:
            恢复后的员工对象

        Raises:
            NotFoundError: 员工不存在时抛出
        """
        # 获取包含软删除的记录
        db_obj = self.get_with_deleted(session, employee_id)
        if db_obj is None:
            raise NotFoundError(model_name=self.model.__name__, identifier=employee_id)

        # 重置软删除标记
        db_obj.is_deleted = False
        db_obj.deleted_at = None
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj


# =============================================================================
# 主程序
# =============================================================================


def main():
    """主函数"""

    # 配置数据库
    database_url = "sqlite:///advanced_example.db"
    db = DatabaseManager(database_url, echo=False)

    # 创建数据库表
    print("=" * 60)
    print("创建数据库表...")
    db.create_tables()
    print("✓ 数据库表创建成功")

    # 初始化 CRUD 实例
    dept_crud = DepartmentCRUD()
    emp_crud = EmployeeCRUD()

    # ==========================================================================
    # 1. 创建部门和员工
    # ==========================================================================
    print("\n" + "=" * 60)
    print("1. 创建部门和员工")
    print("=" * 60)

    # 保存部门ID供后续使用
    tech_dept_id = None
    sales_dept_id = None

    with db.get_session() as session:
        # 创建部门
        tech_dept = dept_crud.create(
            session,
            DepartmentCreate(name="技术部", code="TECH", description="负责产品研发"),
        )
        tech_dept_id = tech_dept.id
        print(f"✓ 创建部门: {tech_dept.name} ({tech_dept.code})")

        sales_dept = dept_crud.create(
            session,
            DepartmentCreate(name="销售部", code="SALES", description="负责市场销售"),
        )
        sales_dept_id = sales_dept.id
        print(f"✓ 创建部门: {sales_dept.name} ({sales_dept.code})")

        # 创建员工
        employees_data = [
            {
                "name": "张三",
                "email": "zhangsan@company.com",
                "salary": 15000.0,
                "department_id": tech_dept_id,
            },
            {
                "name": "李四",
                "email": "lisi@company.com",
                "salary": 12000.0,
                "department_id": tech_dept_id,
            },
            {
                "name": "王五",
                "email": "wangwu@company.com",
                "salary": 20000.0,
                "department_id": tech_dept_id,
            },
            {
                "name": "赵六",
                "email": "zhaoliu@company.com",
                "salary": 8000.0,
                "department_id": sales_dept_id,
            },
            {
                "name": "钱七",
                "email": "qianqi@company.com",
                "salary": 9000.0,
                "department_id": sales_dept_id,
            },
            {
                "name": "孙八",
                "email": "sunba@company.com",
                "salary": 25000.0,
                "department_id": tech_dept_id,
                "is_active": False,
            },
        ]

        for emp_data in employees_data:
            emp = emp_crud.create(session, EmployeeCreate(**emp_data))
            print(f"✓ 创建员工: {emp.name} (薪资: {emp.salary})")

    # ==========================================================================
    # 2. 复杂查询
    # ==========================================================================
    print("\n" + "=" * 60)
    print("2. 复杂查询")
    print("=" * 60)

    with db.get_session() as session:
        # 查询技术部员工
        tech_employees = emp_crud.get_by_department(session, tech_dept_id)
        print(f"✓ 技术部员工 ({len(tech_employees)}人):")
        for emp in tech_employees:
            print(f"  - {emp.name}: {emp.salary}")

        # 查询高薪员工
        high_earners = emp_crud.get_high_earners(session, threshold=10000.0)
        print(f"\n✓ 高薪员工 (>{10000}):")
        for emp in high_earners:
            print(f"  - {emp.name}: {emp.salary}")

        # 查询在职且薪资>10000的员工
        active_well_paid = emp_crud.get_active_employees(session, min_salary=10000.0)
        print(f"\n✓ 在职高薪员工:")
        for emp in active_well_paid:
            print(f"  - {emp.name}: {emp.salary}")

    # ==========================================================================
    # 3. 批量操作
    # ==========================================================================
    print("\n" + "=" * 60)
    print("3. 批量操作")
    print("=" * 60)

    with db.get_session() as session:
        # 批量创建员工
        batch_employees = emp_crud.create_multi(
            session,
            [
                EmployeeCreate(
                    name="周九",
                    email="zhoujiu@company.com",
                    salary=11000.0,
                    department_id=tech_dept_id,
                ),
                EmployeeCreate(
                    name="吴十",
                    email="wushi@company.com",
                    salary=13000.0,
                    department_id=tech_dept_id,
                ),
                EmployeeCreate(
                    name="郑十一",
                    email="zhengshiyi@company.com",
                    salary=8500.0,
                    department_id=sales_dept_id,
                ),
            ],
        )
        print(f"✓ 批量创建 {len(batch_employees)} 个员工")

        # 批量更新部门
        # 将一些员工调到销售部
        updated_count = emp_crud.batch_update_department(
            session, employee_ids=[2, 3], new_department_id=sales_dept_id  # 李四、王五
        )
        print(f"✓ 批量更新 {updated_count} 个员工的部门")

    # ==========================================================================
    # 4. 自定义验证
    # ==========================================================================
    print("\n" + "=" * 60)
    print("4. 自定义验证")
    print("=" * 60)

    with db.get_session() as session:
        # 正常更新薪资
        updated = emp_crud.update_salary(session, 1, 16000.0)
        print(f"✓ 更新薪资成功: {updated.name} -> {updated.salary}")

        # 尝试设置负数薪资（会失败）
        try:
            emp_crud.update_salary(session, 1, -1000.0)
        except ValidationError as e:
            print(f"✓ 捕获验证错误: {e}")

    # ==========================================================================
    # 5. 统计和分页
    # ==========================================================================
    print("\n" + "=" * 60)
    print("5. 统计和分页")
    print("=" * 60)

    with db.get_session() as session:
        # 统计总数
        total_employees = emp_crud.count(session)
        print(f"✓ 员工总数: {total_employees}")

        # 统计在职员工
        active_count = emp_crud.count(session, filters={"is_active": True})
        print(f"✓ 在职员工数: {active_count}")

        # 统计技术部员工
        tech_count = emp_crud.count(session, filters={"department_id": tech_dept_id})
        print(f"✓ 技术部员工数: {tech_count}")

        # 分页查询
        print("\n✓ 分页查询 (每页3条):")
        page1 = emp_crud.get_multi(session, skip=0, limit=3)
        print(f"  第1页: {[e.name for e in page1]}")

        page2 = emp_crud.get_multi(session, skip=3, limit=3)
        print(f"  第2页: {[e.name for e in page2]}")

    # ==========================================================================
    # 6. 使用独立模型进行更新
    # ==========================================================================
    print("\n" + "=" * 60)
    print("6. 使用独立模型进行更新")
    print("=" * 60)

    with db.get_session() as session:
        # 使用 DepartmentUpdate 模型（部分更新）
        updated_dept = dept_crud.update(
            session,
            tech_dept_id,
            DepartmentUpdate(description="负责产品研发和技术支持"),
        )
        print(f"✓ 更新部门描述: {updated_dept.description}")

        # 验证其他字段未被修改
        print(f"✓ 部门名称保持不变: {updated_dept.name}")

    # ==========================================================================
    # 7. 自定义查询方法
    # ==========================================================================
    print("\n" + "=" * 60)
    print("7. 自定义查询方法")
    print("=" * 60)

    with db.get_session() as session:
        # 根据邮箱查找
        emp = emp_crud.get_by_email(session, "zhangsan@company.com")
        print(f"✓ 根据邮箱查找: {emp.name if emp else '未找到'}")

        # 根据编码查找部门
        dept = dept_crud.get_by_code(session, "SALES")
        print(f"✓ 根据编码查找部门: {dept.name if dept else '未找到'}")

    # ==========================================================================
    # 8. 软删除功能演示
    # ==========================================================================
    print("\n" + "=" * 60)
    print("8. 软删除功能演示")
    print("=" * 60)

    with db.get_session() as session:
        # 先创建几个用于演示软删除的员工
        soft_delete_emps = emp_crud.create_multi(
            session,
            [
                EmployeeCreate(
                    name="软删测试1",
                    email="softdelete1@company.com",
                    salary=10000.0,
                    department_id=tech_dept_id,
                ),
                EmployeeCreate(
                    name="软删测试2",
                    email="softdelete2@company.com",
                    salary=12000.0,
                    department_id=tech_dept_id,
                ),
                EmployeeCreate(
                    name="软删测试3",
                    email="softdelete3@company.com",
                    salary=15000.0,
                    department_id=sales_dept_id,
                ),
            ],
        )
        print(f"✓ 创建 {len(soft_delete_emps)} 个员工用于软删除演示")

        # 记录ID用于后续操作
        soft_emp_id_1 = soft_delete_emps[0].id
        soft_emp_id_2 = soft_delete_emps[1].id
        soft_emp_id_3 = soft_delete_emps[2].id

        # 查看删除前的总数
        count_before = emp_crud.count(session)
        print(f"✓ 软删除前员工总数: {count_before}")

        # 执行软删除 (使用 delete 方法并传入 soft=True)
        deleted_emp = emp_crud.delete(session, soft_emp_id_1, soft=True)
        print(f"✓ 软删除员工: {deleted_emp.name}")
        print(f"  - is_deleted: {deleted_emp.is_deleted}")
        print(f"  - deleted_at: {deleted_emp.deleted_at}")

        # 验证软删除后普通查询查不到
        found = emp_crud.get(session, soft_emp_id_1)
        print(f"✓ 软删除后普通查询结果: {'未找到' if found is None else '找到'}")

        # 验证 exists 方法 (软删除后 exists 返回 False)
        exists = emp_crud.exists(session, soft_emp_id_1)
        print(f"✓ 软删除后 exists 查询: {exists}")

        # 查看软删除后的总数（不包含已软删除的）
        count_after = emp_crud.count(session)
        print(
            f"✓ 软删除后员工总数: {count_after} (减少了 {count_before - count_after})"
        )

        # 软删除第二个员工
        emp_crud.delete(session, soft_emp_id_2, soft=True)
        print(f"✓ 软删除第二个员工 (ID: {soft_emp_id_2})")

        # 使用 get_multi 验证过滤效果
        all_active = emp_crud.get_multi(session, limit=100)
        print(f"✓ get_multi 返回的非删除员工数: {len(all_active)}")

        # 硬删除对比（彻底删除）
        print("\n✓ 执行硬删除对比:")
        emp_crud.delete(session, soft_emp_id_3, soft=False)  # 硬删除
        exists_hard = emp_crud.exists(session, soft_emp_id_3)
        print(f"  - 硬删除后 exists 查询: {exists_hard}")

        # 恢复软删除的员工 (使用自定义 restore 方法)
        print("\n✓ 恢复软删除的员工:")
        restored = emp_crud.restore(session, soft_emp_id_1)
        print(f"  - 恢复员工: {restored.name}")
        print(f"  - is_deleted: {restored.is_deleted}")
        print(f"  - deleted_at: {restored.deleted_at}")

        # 验证恢复后可以被查询到
        found_after_restore = emp_crud.get(session, soft_emp_id_1)
        print(f"  - 恢复后普通查询结果: {'找到' if found_after_restore else '未找到'}")

    # ==========================================================================
    # 9. 分批插入功能演示
    # ==========================================================================
    print("\n" + "=" * 60)
    print("9. 分批插入功能演示")
    print("=" * 60)

    with db.get_session() as session:
        # 批量创建25个员工，每批5个
        batch_employees_data = [
            EmployeeCreate(
                name=f"批量员工_{i:02d}",
                email=f"batchemployee_{i:02d}@company.com",
                salary=8000.0 + i * 100,
                department_id=tech_dept_id,
            )
            for i in range(25)
        ]

        print(f"✓ 准备批量创建 {len(batch_employees_data)} 个员工")
        print(f"✓ 使用 batch_size=5 进行分批处理\n")

        # 使用分批插入
        created_employees = emp_crud.create_multi(
            session,
            batch_employees_data,
            batch_size=5,
        )

        print(f"\n✓ 分批插入完成，共创建 {len(created_employees)} 个员工")

        # 验证插入结果
        total_count = emp_crud.count(session)
        print(f"✓ 当前员工总数: {total_count}")

        # 显示部分创建的员工
        print("\n✓ 显示前10个创建的员工:")
        for emp in created_employees[:10]:
            print(f"  - {emp.name}: {emp.email}, 薪资: {emp.salary}")

        if len(created_employees) > 10:
            print(f"  ... 还有 {len(created_employees) - 10} 个员工")

    # ==========================================================================
    # 清理
    # ==========================================================================
    print("\n" + "=" * 60)
    print("清理数据库...")
    db.drop_tables()
    db.close()
    print("✓ 数据库已清理")

    print("\n" + "=" * 60)
    print("高级示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
