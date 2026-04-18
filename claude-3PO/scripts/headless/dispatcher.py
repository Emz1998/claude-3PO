class Headless():

    def __init__(self, config, state):
        self.config = config
        self.state = state

    def call_reviewer(self, review_type: ["plan", "code", "test"]) -> None:
