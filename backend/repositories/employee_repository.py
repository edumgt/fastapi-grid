from typing import Any

from backend.config.database import DynamoDbClientFactory


class EmployeeRepository:
    def __init__(self):
        self.table = DynamoDbClientFactory.table()

    def save(self, employee: dict[str, Any]) -> None:
        self.table.put_item(Item=employee)

    def find_by_id_and_name(self, employee_id: str, name: str) -> dict[str, Any] | None:
        response = self.table.get_item(Key={"id": employee_id, "name": name})
        return response.get("Item")

    def delete_by_id_and_name(self, employee_id: str, name: str) -> None:
        self.table.delete_item(Key={"id": employee_id, "name": name})

    def find_all(self) -> list[dict[str, Any]]:
        response = self.table.scan()
        return response.get("Items", [])
