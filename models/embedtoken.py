class EmbedToken:
    tokenId = None
    token = None
    tokenExpiry = None

    def __init__(self, token_id, token, token_expiry):
        self.tokenId = token_id
        self.token = token
        self.tokenExpiry = token_expiry