from datetime import date

from dateutil.relativedelta import relativedelta

from ..utils.model_helper import get_value


class HrContractService:
    filter_dict = {
        "expire_in_1_month": [
            (
                "date_end",
                "<=",
                ((date.today() + relativedelta(months=1)).strftime("%Y-%m-%d")),
            )
        ],
        "expire_in_2_month": [
            (
                "date_end",
                "<=",
                ((date.today() + relativedelta(months=2)).strftime("%Y-%m-%d")),
            )
        ],
    }

    def __init__(self, request):
        self.env = request.env

    def get_contracts_count(self, filter):  # pylint: disable=redefined-builtin
        search_filter = self.filter_dict[filter] if filter else []
        contracts_count = self.env["hr.contract.history"].search_count(search_filter)

        return contracts_count

    def get_contracts(  # pylint: disable=redefined-builtin
        self, limit=10, offset=0, filter=None
    ):
        search_filter = self.filter_dict[filter] if filter else []
        contracts = self.env["hr.contract.history"].search(
            search_filter,
            limit=limit,
            offset=offset,
            order="employee_id",
        )
        return [
            {
                "contract_type": get_value(contract.contract_type_id, "code"),
                "date_start": get_value(contract, "date_start"),
                "date_end": get_value(contract, "date_end"),
                "employee_name": get_value(contract.employee_id, "name"),
                "employee_kid": get_value(contract.employee_id, "kid"),
                "master_department": get_value(
                    contract.employee_id.master_department_id, "name"
                ),
                "state": get_value(contract, "state"),
            }
            for contract in contracts
        ]
