from .employee_response import EmployeeService
from .utils import get_data


class EmployeeContractResponse:
    def __init__(self, employee):
        self.__employee_service = EmployeeService(employee)

    def to_json(self):
        contracts = []

        contractModel = self.__employee_service.get_contracts()

        for relative in contractModel:
            contracts.append(
                {
                    "contract_type": get_data(relative, "contract_type_id.code"),
                    "date_start": get_data(relative, "date_start"),
                    "date_end": get_data(relative, "date_end"),
                    "duration": get_data(relative, "duration"),
                    "evaluation_date": get_data(relative, "date_evaluation"),
                    "note": get_data(relative, "notes"),
                }
            )
        return contracts
