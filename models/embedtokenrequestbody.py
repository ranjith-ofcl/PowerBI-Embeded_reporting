class EmbedTokenRequestBody:
    datasets = None
    reports = None
    targetWorkspaces = None

    def __init__(self):
        self.datasets = []
        self.reports = []
        self.targetWorkspaces = []