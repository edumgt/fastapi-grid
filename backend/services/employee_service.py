from backend.models.employee import EmployeeCreate
from backend.repositories.employee_repository import EmployeeRepository


class EmployeeService:
    def __init__(self, repository: EmployeeRepository):
        self.repository = repository

    def create(self, employee: EmployeeCreate) -> None:
        self.repository.save(employee.model_dump())

    def get(self, employee_id: str, name: str) -> dict | None:
        return self.repository.find_by_id_and_name(employee_id, name)

    def delete(self, employee_id: str, name: str) -> None:
        self.repository.delete_by_id_and_name(employee_id, name)

    def list_all(self) -> list[dict]:
        return self.repository.find_all()
