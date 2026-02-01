import re
import json
import os

class InterviewEngine:
    """
    Resume + JD aware interview engine with:
    - JD auto-expansion for short titles
    - Strict JD validation
    - Dataset-backed answer validation
    """

    TITLE_JD_MAP = {
        "sde": (
            "Software Development Engineer role requiring strong knowledge of "
            "data structures, algorithms, Python, APIs, databases, system design, "
            "and problem-solving skills."
        ),
        "software engineer": (
            "Software Engineer role involving backend and frontend development, "
            "working with APIs, databases, and scalable system design."
        ),
        "backend developer": (
            "Backend Developer role focused on APIs, databases, authentication, "
            "and server-side system design."
        )
    }

    def __init__(self, resume_text: str, jd_text: str):
        self.resume = resume_text.lower()
        self.raw_jd = jd_text.strip().lower()

        # Auto-expand JD if it's just a title
        self.jd = self._expand_jd_if_needed(self.raw_jd)
        self.inferred_jd = self.jd if self.raw_jd != self.jd else None

        self.question_index = 0

        # Load skill dataset
        self.skill_knowledge = self._load_skill_knowledge()

        # Extract skills
        self.resume_skills = self._extract_skills(self.resume)
        self.jd_skills = self._extract_skills(self.jd)

        self.primary_skill = (
            self.resume_skills[0] if self.resume_skills else "your main technical skill"
        )
        self.primary_project = self._extract_primary_project()

        self.evidence = {
            "clarity": [],
            "depth": [],
            "ownership": [],
            "resume_relevance": [],
            "jd_relevance": [],
            "skill_coverage": []
        }

    def _expand_jd_if_needed(self, jd: str):
        if len(jd.split()) <= 3:
            return self.TITLE_JD_MAP.get(jd, jd)
        return jd

    def _load_skill_knowledge(self):
        path = os.path.join(os.path.dirname(__file__), "skill_knowledge.json")
        with open(path, "r") as f:
            return json.load(f)

    def is_invalid_text(self, text: str, min_words: int):
        if not text or not text.strip():
            return True
        if len(text.strip().split()) < min_words:
            return True
        if re.fullmatch(r"[\W\d_]+", text.strip()):
            return True
        return False

    def validate_jd(self):
        if self.is_invalid_text(self.jd, min_words=15):
            return False, "The Job Description is too short or unclear."

        if not self.jd_skills:
            return False, "The Job Description does not contain clear technical requirements."

        return True, ""

    def _extract_skills(self, text):
        return [k for k in self.skill_knowledge.keys() if k in text]

    def _extract_primary_project(self):
        for line in self.resume.split("\n"):
            if any(w in line for w in ["project", "built", "developed", "designed"]):
                return line.strip()
        return "a project you worked on"

    def next_question(self):
        self.question_index += 1

        if self.question_index == 1:
            return (
                f"I noticed you mentioned {self.primary_skill}. "
                f"Can you explain how you actually used it?"
            )

        if self.question_index == 2:
            return (
                f"You mentioned {self.primary_project}. "
                f"Can you walk me through what you personally worked on?"
            )

        if self.question_index == 3:
            return (
                "Considering the role you’re applying for, "
                "what was the most challenging part of your work, "
                "and how does it prepare you for this position?"
            )

        return None

    def _skill_coverage_score(self, answer: str):
        if self.primary_skill not in self.skill_knowledge:
            return 1.0
        expected = self.skill_knowledge[self.primary_skill]
        mentioned = [k for k in expected if k in answer.lower()]
        return len(mentioned) / len(expected) if expected else 1.0

    def evaluate_answer(self, answer: str):
        if self.is_invalid_text(answer, min_words=5):
            return {
                "valid": False,
                "comment": "I’m not getting enough information from that answer. Please explain properly."
            }

        answer_l = answer.lower()
        wc = len(answer.split())

        clarity = 1 if wc >= 30 else 0
        depth = 1 if any(k in answer_l for k in ["because", "for example", "trade-off", "decision"]) else 0
        ownership = 1 if " i " in f" {answer_l} " else 0
        resume_rel = 1 if any(s in answer_l for s in self.resume_skills) else 0
        jd_rel = 1 if any(s in answer_l for s in self.jd_skills) else 0
        coverage = self._skill_coverage_score(answer)

        self.evidence["clarity"].append(clarity)
        self.evidence["depth"].append(depth)
        self.evidence["ownership"].append(ownership)
        self.evidence["resume_relevance"].append(resume_rel)
        self.evidence["jd_relevance"].append(jd_rel)
        self.evidence["skill_coverage"].append(coverage)

        if coverage < 0.4:
            comment = f"You mentioned {self.primary_skill}, but didn’t cover its core concepts."
        elif resume_rel and jd_rel:
            comment = "Good answer. You connected your experience well to the role."
        else:
            comment = "Alright, let’s move on."

        return {"valid": True, "comment": comment}

    def final_report(self):
        report = {k: sum(v) / len(v) for k, v in self.evidence.items()}
        score = (
            report["clarity"] * 15 +
            report["depth"] * 20 +
            report["ownership"] * 15 +
            report["resume_relevance"] * 15 +
            report["jd_relevance"] * 20 +
            report["skill_coverage"] * 15
        )
        strengths = [k for k, v in report.items() if v >= 0.7]
        weaknesses = [k for k, v in report.items() if v < 0.5]
        return round(score, 2), report, strengths, weaknesses