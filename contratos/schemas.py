CONTRATO_CREATE_SCHEMA = {
    
    "required":[
        "cont_clie",
        "cont_data",
        "cont_prod",
        "cont_unit",
        "cont_quan",
        "cont_tota"
        
    ],
        "types":{
            "cont_clie": int,
            "cont_data": "date",
            "cont_prod": str,
            "cont_unit": float,
            "cont_quan": float,
            "cont_tota": float
        }
}