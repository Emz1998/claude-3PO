from lib.state_store import StateStore  # type: ignore
from utils import logger  # type: ignore


class Resolver:
    def __init__(self, state: StateStore):
        self.state = state

    #  ────────────────── Plan ────────────────────────

    def is_plan_phase_done(self) -> bool:
        reviews = self.state.get_reviews(review_type="plan")
        return all(review["status"] == "completed" for review in reviews)

    def resolve_plan(self) -> bool:
        if self.is_plan_phase_done():
            self.state.update_review(
                review_type="plan", status="completed", verdict="pass"
            )
        return True

    #  ────────────────── Test ────────────────────────
    def is_test_done(self) -> bool:
        reviews = self.state.get_reviews(review_type="test")
        return all(review["status"] == "completed" for review in reviews)

    def resolve_test(self) -> bool:
        if self.is_test_done():
            self.state.update_review(
                review_type="test", status="completed", verdict="pass"
            )
        return True

    def explorers_done(self) -> bool:
        agents = self.state.get_agents(status="completed")
        return all(agent["name"] == "Explore" for agent in agents)

    def researchers_done(self) -> bool:
        agents = self.state.get_agents(status="completed")
        return all(agent["name"] == "Research" for agent in agents)

    def resolve_explore_skill(self) -> bool:
        if self.explorers_done():
            self.state.update_skill_status(name="Explore", status="completed")
        return True

    def resolve_research_skill(self) -> bool:
        if self.researchers_done():
            self.state.update_skill_status(name="Research", status="completed")
        return True

    def is_plan_written(self) -> bool:
        plan_file_path = self.state.get_file_path(type="plan")
        return len(plan_file_path) > 0

    def is_plan_review_done(self) -> bool:
        reviews = self.state.get_reviews(review_type="plan")
        return all(review["status"] == "completed" for review in reviews)

    def resolve_plan_skill(self) -> bool:
        if not self.is_plan_written():
            return False
        if not self.is_plan_review_done():
            return False
        self.state.update_skill_status(name="Plan", status="completed")
        return True

    def is_test_written(self) -> bool:
        test_file_path = self.state.get_file_path(type="test")
        return len(test_file_path) > 0

    def is_test_review_done(self) -> bool:
        reviews = self.state.get_reviews(review_type="test")
        return all(review["status"] == "completed" for review in reviews)

    def resolve_test_skill(self) -> bool:
        if not self.is_test_written():
            return False
        if not self.is_test_review_done():
            return False

        self.state.update_skill_status(name="Test", status="completed")
        return True

    def is_coding_done(self) -> bool:
        test_status = self.state.test_status
        return test_status == "pass"

    def resolve_coding_skill(self) -> bool:
        if not self.is_coding_done():
            return False
        self.state.update_skill_status(name="Coding", status="completed")
        return True

    def is_qa_specialist_done(self) -> bool:
        qa_specialist_status = self.state.get_agent_status(name="QASpecialist")
        return qa_specialist_status == "completed"

    def resolve_validation_skill(self) -> bool:
        if not self.is_qa_specialist_done():
            return False
        self.state.update_skill_status(name="Validate", status="completed")
        return True

    def resolve_task_created(self) -> bool:
        if not self.state.tasks_created:
            return False
        self.state.update_skill_status(name="create-tasks", status="completed")
        return True

    def resolve(self) -> None:
        resolvers = [
            self.resolve_plan,
            self.resolve_test,
            self.resolve_explore_skill,
            self.resolve_research_skill,
            self.resolve_plan_skill,
            self.resolve_test_skill,
            self.resolve_coding_skill,
            self.resolve_validation_skill,
        ]
        for resolver in resolvers:
            if not resolver():
                logger.log_message(f"Resolver {resolver.__name__} failed")
