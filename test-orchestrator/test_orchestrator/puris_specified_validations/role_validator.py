
customer_semantic_models = ["urn:samm:io.catenax.short_term_material_demand",
            "urn:samm:io.catenax.item_stock",
            "urn:samm:io.catenax.delivery_information",
            "urn:samm:io.catenax.days_of_supply"]

supplier_semantic_models = ["urn:samm:io.catenax.planned_production_output",
            "urn:samm:io.catenax.item_stock",
            "urn:samm:io.catenax.delivery_information",
            "urn:samm:io.catenax.days_of_supply"]

def validate_role(shell_descriptor, partner_role):

    partner_role = partner_role.lower()
    found_semantic_models = set()
    submodels = shell_descriptor.get("submodelDescriptors", [])

    for submodel in submodels:
        semantic_id = submodel.get("semanticId", {})
        keys = semantic_id.get("keys", [])
        if isinstance(keys, list):
            for key in keys:
                value = key.get("value")
                semantic_model = value.split("#")[0].rsplit(":", 1)[0]
                found_semantic_models.add(semantic_model)

    if partner_role == "customer":
        expected_semantic_models = set(customer_semantic_models)
        missing_models = expected_semantic_models - found_semantic_models
        if len(missing_models) == 0:
            return {"Success": "The Customer provides all expected submodels for it's Role."}
        else:
            return {"Warning": "The customer does not provide all submodels.",
                    'Provided': found_semantic_models,
                    'Missing': missing_models}
    elif partner_role == "supplier":
        expected_semantic_models = set(supplier_semantic_models)
        missing_models = expected_semantic_models - found_semantic_models
        if len(missing_models) == 0:
            return {"Success: The Supplier provides all expected submodels for it's Role."}
        else:
            return {"Warning": "The supplier does not provide all submodels.",
                    'Provided': found_semantic_models,
                    'Missing': missing_models}
    else:
        return {f"Failure: The Partner Role '{partner_role}' is not Part of Data providing/consuming in the Puris Use Case. "
                f"Use 'customer' or 'supplier'"}


def check_submodel_direction_value(partner_role, semantic_name, submodel):
    partner_role = partner_role.lower()
    if partner_role is None:
        return 'The Partner Role must be given to check the direction value of the submodel.'

    direction = submodel.get("direction", "")
    if direction == 'INBOUND' and partner_role == 'customer':
        return {'Success': f'The values for {semantic_name} is set correctly.'}
    elif direction == 'OUTBOUND' and partner_role == 'customer':
        return {'WARN': 'The value is set falsely.',
                'Details': f'The direction in {semantic_name} for Customer is INBOUND.'}
    elif direction == 'INBOUND' and partner_role == 'supplier':
        return {'WARN': 'The value is set falsely.',
                'Details': f'The direction in {semantic_name} for Supplier is OUTBOUND.'}
    elif direction == 'OUTBOUND' and partner_role == 'supplier':
        return {'Success': f'The values for {semantic_name} is set correctly.'}
    else:
        return {'Failure': 'Something went wrong by parsing the submodel'}