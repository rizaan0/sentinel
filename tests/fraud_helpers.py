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
    return client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": recipient_account_number,
            "amount": amount,
            "remark": remark,
            "pin": pin,
        },
        headers=headers,
    )
