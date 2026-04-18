revise @claude-3PO/scripts/utils/recorder.py . The Recorder class should only consist of methods:

1. record_plan(file_path:str, written:bool, revised: bool, reviews:list)
2. record_tests(file_path:tuple[Literal["add", "replace], list[<file_paths>]], executed:bool, reviews:list, files_to_revise: tuple[Literal["add", "replace], list[<file_paths>]], files_revised: tuple[Literal["add", "replace], list[<file_paths>]],)
3. record_code_files(...) Note: arguments should be file_paths, reviews, files_to_revise, files_revised. All has an argument of tuple ("add or replace", file_paths)

4. record_report_written(file_path: str, written:bool)
5. record_command()
6. record_session_id()
7. record_story_id()
8. record_workflow_type()
9. record_workflow_active()
10. record_worfklow_status()
11. record_workflow(key: (type, active, status))

12. record_test_mode()
13. record_phase() (append a dict like before)
14. record_tdd()
15. record_validation_result(Literal["pass" , "fail"])
16. record_agent(name:str, status:Literal["in_progress", "completed", "failed"], tool_use_id:str)
17. record_code_review(iteration, scores, status)
18. record_test_review(iteration, verdict, status)
19. record_task(task_id:str, subject:str, description:str, parent_task_id:str) Add a Task model in state.py. parent task id is optional
