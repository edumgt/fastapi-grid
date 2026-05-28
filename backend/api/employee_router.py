from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.models.employee import EmployeeCreate, EmployeeRead
from backend.repositories.employee_repository import EmployeeRepository
from backend.services.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["employees"])


def get_employee_service() -> EmployeeService:
    return EmployeeService(EmployeeRepository())


@router.post("", status_code=status.HTTP_201_CREATED)
def create_employee(employee: EmployeeCreate, service: EmployeeService = Depends(get_employee_service)):
    service.create(employee)
    return {"message": "Employee added to DynamoDB."}


@router.get("/{employee_id}/{name}", response_model=EmployeeRead)
def get_employee(employee_id: str, name: str, service: EmployeeService = Depends(get_employee_service)):
    item = service.get(employee_id, name)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return item


@router.delete("/{employee_id}/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: str, name: str, service: EmployeeService = Depends(get_employee_service)):
    service.delete(employee_id, name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=list[EmployeeRead])
def list_employees(service: EmployeeService = Depends(get_employee_service)):
    return service.list_all()
