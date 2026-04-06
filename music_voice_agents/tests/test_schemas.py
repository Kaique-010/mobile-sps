from app.schemas import SingRequest


def test_sing_request_accepts_valid_voice() -> None:
    payload = SingRequest(voice="tenor")
    assert payload.voice == "tenor"
