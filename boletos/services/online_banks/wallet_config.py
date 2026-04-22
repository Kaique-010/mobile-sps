def clean_wallet_value(value):
    return str(value or '').strip()


def validate_online_wallet_config(carteira, bank_name='Banco'):
    client_id = clean_wallet_value(getattr(carteira, 'cart_webs_clie_id', ''))
    client_secret = clean_wallet_value(getattr(carteira, 'cart_webs_clie_secr', ''))
    base = clean_wallet_value(getattr(carteira, 'cart_webs_ssl_lib', ''))

    if not client_id or not client_secret:
        raise ValueError(f'Carteira sem client_id/client_secret configurados para {bank_name}.')

    return {
        'client_id': client_id,
        'client_secret': client_secret,
        'base': base,
        'scope': clean_wallet_value(getattr(carteira, 'cart_webs_scop', '')),
        'api_key': clean_wallet_value(getattr(carteira, 'cart_webs_user_key', '')),
    }
