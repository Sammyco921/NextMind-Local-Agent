from __future__ import annotations

from core.human_normalizer import HumanNormalizer


class TestAbbreviationExpansion:
    def test_ui_to_user_interface(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("fix the ui")
        assert "user interface" in r.normalized

    def test_pls_to_please(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("pls create a file")
        assert "please" in r.normalized

    def test_proj_to_project(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("clean up the proj")
        assert "project" in r.normalized

    def test_doc_to_document(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("list the docs")
        assert "documents" in r.normalized

    def test_w_with_to_with(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("file w/ content")
        assert "with" in r.normalized

    def test_dont_to_do_not(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("dont create")
        assert "do not" in r.normalized

    def test_multiple_abbreviations(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("pls fix the ui proj")
        assert "please" in r.normalized
        assert "user interface" in r.normalized
        assert "project" in r.normalized


class TestContinuationDetection:
    def test_continue_with_active_goal(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("continue", active_goal_descriptions=["fix the project structure"])
        assert r.is_continuation
        assert r.normalized == "fix the project structure"

    def test_keep_going_with_active_goal(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("keep going", active_goal_descriptions=["setup project structure"])
        assert r.is_continuation
        assert r.normalized == "setup project structure"

    def test_finish_this_with_active_goal(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("finish this", active_goal_descriptions=["write config file"])
        assert r.is_continuation
        assert r.normalized == "write config file"

    def test_pick_up_where_we_left_off(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("pick up where we left off", active_goal_descriptions=["implement parser"])
        assert r.is_continuation
        assert r.normalized == "implement parser"

    def test_continue_no_active_goal(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("continue")
        assert not r.is_continuation
        assert r.normalized == "continue"

    def test_continue_not_detected_in_sentence(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("please continue working on the project", active_goal_descriptions=["setup project"])
        # "continue" in a longer sentence should NOT trigger continuation detection
        assert not r.is_continuation

    def test_carry_on(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("carry on", active_goal_descriptions=["fix bugs"])
        assert r.is_continuation

    def test_proceed(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("proceed", active_goal_descriptions=["write tests"])
        assert r.is_continuation

    def test_resume(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("resume", active_goal_descriptions=["refactor code"])
        assert r.is_continuation


class TestVagueDirectives:
    def test_clean_up_project_lists_directory(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("clean up the project")
        assert "list directory" in r.normalized

    def test_cleanup_shorthand(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("cleanup")
        assert "list directory" in r.normalized

    def test_tidy_up(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("tidy the project")
        assert "list directory" in r.normalized

    def test_organize(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("organize the files")
        assert "list directory" in r.normalized

    def test_specific_goal_not_vague(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("create file hello.txt with content")
        assert "list directory" not in r.normalized


class TestWhitespacePunctuation:
    def test_multiple_spaces_normalized(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("create   file    hello.txt")
        assert "  " not in r.normalized

    def test_trailing_punctuation_removed(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("list files!")
        assert not r.normalized.endswith("!")

    def test_question_mark_removed(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("can you list the files?")
        assert not r.normalized.endswith("?")


class TestDeterminism:
    def test_identical_input_same_output(self) -> None:
        n = HumanNormalizer()
        a = n.normalize("fix the ui proj", active_goal_descriptions=["test goal"])
        b = n.normalize("fix the ui proj", active_goal_descriptions=["test goal"])
        assert a.normalized == b.normalized
        assert a.transformations == b.transformations

    def test_no_active_goals_no_continuation_detection(self) -> None:
        n = HumanNormalizer()
        a = n.normalize("continue")
        b = n.normalize("continue")
        assert a == b

    def test_empty_input(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("")
        assert r.normalized == ""


class TestIntegration:
    def test_fix_ui_normalizes_and_can_be_detected(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("fix the ui")
        # After normalization: "fix the user interface"
        from core.intent_clarifier import IntentClarifier
        c = IntentClarifier()
        result = c.clarify(r.normalized)
        # "fix" is now in _WRITE_KEYWORDS, so it should be detected as write_file
        assert "write_file" in result.detected_tools

    def test_clean_up_project_is_executable_after_normalization(self) -> None:
        n = HumanNormalizer()
        r = n.normalize("clean up the project")
        from core.intent_clarifier import IntentClarifier
        c = IntentClarifier()
        result = c.clarify(r.normalized)
        # Should be detected as list_dir
        assert "list_dir" in result.detected_tools
