def signup_with_pin(client, email, password="supersecret1", pin="1234"):
    signup = client.post(
        "/api/v1/auth/signup",
        json={"full_name": email.split("@")[0], "email": email, "password": password},
    )
    body = signup.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    client.post("/api/v1/pin/setup", json={"pin": pin}, headers=headers)
    return body["user"], headers


def transfer(client, headers, recipient_account_number, amount, pin, remark=None):
    import uuid

    key = str(uuid.uuid4())
    response = client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": recipient_account_number,
            "amount": amount,
            "remark": remark,
            "pin": pin,
            "idempotency_key": key[:64],
        },
        headers=headers,
    )
    if response.status_code != 428:
        return response
    body = response.json()
    return client.post(
        "/api/v1/transactions/transfer/confirm",
        json={
            "challenge_id": body["challenge_id"],
            "code": body["code"],
            "idempotency_key": key[:64],
        },
        headers=headers,
    )
