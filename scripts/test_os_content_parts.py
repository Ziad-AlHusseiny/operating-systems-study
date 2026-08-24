import hashlib
import json
import re
import unittest
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTRACTION_PATH = ROOT / "extraction" / "os-pages.json"
MANIFEST_PATH = ROOT / "content" / "source-manifest.json"

PART_KEYS = {"version", "modules", "lessons", "questions", "explanations"}
MODULE_KEYS = {"id", "title", "order", "objectiveIds", "sourceRefs"}
LESSON_KEYS = {
    "id", "moduleId", "objectiveIds", "title", "contentVersion",
    "materialSectionIds", "learningObjectives", "materialSections",
    "needsReview", "reviewNotes", "review",
}
OBJECTIVE_KEYS = {"id", "moduleId", "text", "order", "sourceRefs"}
SECTION_KEYS = {
    "id", "order", "title", "origin", "label", "generatedStudyGuidance",
    "summary", "explanation", "body", "keyTerms", "workedExamples",
    "commonMistakes", "examTips", "recap", "sourceRefs",
    "linkedQuestionIds", "needsReview", "reviewNotes",
}
QUESTION_COMMON_KEYS = {
    "id", "origin", "type", "prompt", "topic", "correctAnswer", "rationale",
    "difficulty", "bloomLevel", "cognitiveLevel", "learningObjectiveId",
    "sourceRefs", "generationMethod", "generatedExplanationId", "provenance",
    "evidenceMap", "contentVersion", "qualityState", "reviewState",
    "duplicateComparison", "duplicateDisposition", "needsReview", "reviewNotes",
    "review",
}
EXPLANATION_KEYS = {
    "id", "questionId", "language", "generatedStudyGuidance", "translation",
    "explanation", "body", "note", "contentVersion", "sourceRefs",
    "needsReview", "reviewNotes", "review",
}
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
ARABIC_WORD_RE = re.compile(r"[\u0621-\u064a]+")
EVIDENCE_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "by", "does",
    "for", "from", "in", "into", "is", "it", "its", "of", "on", "or",
    "that", "the", "their", "this", "to", "which", "while", "with",
}
SEMANTIC_STOP_WORDS = EVIDENCE_STOP_WORDS | {
    "answer", "correct", "described", "lecture", "option", "statement",
    "system", "what", "when",
}
VERIFIED_MCQ_ANSWER_KEY = {
    "gq-os-ch01-part1-001": 1,
    "gq-os-ch01-part1-002": 2,
    "gq-os-ch01-part1-003": 0,
    "gq-os-ch01-part1-004": 2,
    "gq-os-ch01-part1-005": 3,
    "gq-os-ch01-part1-006": 0,
    "gq-os-ch01-part2-001": 2,
    "gq-os-ch01-part2-002": 0,
    "gq-os-ch01-part2-003": 2,
    "gq-os-ch01-part2-004": 1,
    "gq-os-ch01-part2-005": 1,
    "gq-os-ch01-part2-006": 2,
    "gq-os-ch01-part3-001": 1,
    "gq-os-ch01-part3-002": 0,
    "gq-os-ch01-part3-003": 0,
    "gq-os-ch01-part3-004": 2,
    "gq-os-ch01-part3-005": 1,
    "gq-os-ch01-part3-006": 0,
    "gq-os-ch01-part4-001": 0,
    "gq-os-ch01-part4-002": 1,
    "gq-os-ch01-part4-003": 1,
    "gq-os-ch01-part4-004": 1,
    "gq-os-ch01-part4-005": 0,
    "gq-os-ch01-part4-006": 1,
    "gq-os-ch02-part1-001": 1,
    "gq-os-ch02-part1-002": 0,
    "gq-os-ch02-part1-003": 1,
    "gq-os-ch02-part1-004": 0,
    "gq-os-ch02-part1-005": 1,
    "gq-os-ch02-part1-006": 1,
    "gq-os-ch02-part2-001": 0,
    "gq-os-ch02-part2-002": 1,
    "gq-os-ch02-part2-003": 1,
    "gq-os-ch02-part2-004": 1,
    "gq-os-ch02-part2-005": 1,
    "gq-os-ch02-part2-006": 1,
    "gq-os-ch02-part3-001": 0,
    "gq-os-ch02-part3-002": 0,
    "gq-os-ch02-part3-003": 2,
    "gq-os-ch02-part3-004": 1,
    "gq-os-ch02-part3-005": 1,
    "gq-os-ch02-part3-006": 1,
    "gq-os-ch03-part1-001": 1,
    "gq-os-ch03-part1-002": 2,
    "gq-os-ch03-part1-003": 0,
    "gq-os-ch03-part1-004": 3,
    "gq-os-ch03-part1-005": 1,
    "gq-os-ch03-part1-006": 2,
    "gq-os-ch03-part2-001": 1,
    "gq-os-ch03-part2-002": 2,
    "gq-os-ch03-part2-003": 0,
    "gq-os-ch03-part2-004": 3,
    "gq-os-ch03-part2-005": 1,
    "gq-os-ch03-part2-006": 2,
    "gq-os-ch03-part3-001": 1,
    "gq-os-ch03-part3-002": 2,
    "gq-os-ch03-part3-003": 0,
    "gq-os-ch03-part3-004": 3,
    "gq-os-ch03-part3-005": 1,
    "gq-os-ch03-part3-006": 2,
    "gq-os-ch05-part1-001": 1,
    "gq-os-ch05-part1-002": 2,
    "gq-os-ch05-part1-003": 0,
    "gq-os-ch05-part1-004": 3,
    "gq-os-ch05-part1-005": 1,
    "gq-os-ch05-part1-006": 2,
    "gq-os-ch05-part2-001": 2,
    "gq-os-ch05-part2-002": 0,
    "gq-os-ch05-part2-003": 3,
    "gq-os-ch05-part2-004": 1,
    "gq-os-ch05-part2-005": 2,
    "gq-os-ch05-part2-006": 3,
    "gq-os-ch05-part3-001": 1,
    "gq-os-ch05-part3-002": 2,
    "gq-os-ch05-part3-003": 0,
    "gq-os-ch05-part3-004": 3,
    "gq-os-ch05-part3-005": 1,
    "gq-os-ch05-part3-006": 2,
    "gq-os-ch05-part4-001": 1,
    "gq-os-ch05-part4-002": 2,
    "gq-os-ch05-part4-003": 0,
    "gq-os-ch05-part4-004": 3,
    "gq-os-ch05-part4-005": 1,
    "gq-os-ch05-part4-006": 2,
}

EXPECTED_NEW_QUESTION_METADATA = {
    "gq-os-ch03-part1-001": ("objective-os-ch03-part1-1", "Process memory", "material-section-os-ch03-part1-process-memory"),
    "gq-os-ch03-part1-002": ("objective-os-ch03-part1-1", "Process state", "material-section-os-ch03-part1-states-trace"),
    "gq-os-ch03-part1-003": ("objective-os-ch03-part1-2", "PCB context", "material-section-os-ch03-part1-pcb-threads"),
    "gq-os-ch03-part1-004": ("objective-os-ch03-part1-3", "Multithreading", "material-section-os-ch03-part1-pcb-threads"),
    "gq-os-ch03-part1-005": ("objective-os-ch03-part1-3", "I/O wait queue", "material-section-os-ch03-part1-scheduling-queues"),
    "gq-os-ch03-part1-006": ("objective-os-ch03-part1-3", "Swapping trade-off", "material-section-os-ch03-part1-scheduling-queues"),
    "gq-os-ch03-part1-007": ("objective-os-ch03-part1-1", "Dynamic memory layout", "material-section-os-ch03-part1-process-memory"),
    "gq-os-ch03-part1-008": ("objective-os-ch03-part1-2", "Linux current pointer", "material-section-os-ch03-part1-pcb-threads"),
    "gq-os-ch03-part1-009": ("objective-os-ch03-part1-3", "Thread state sharing", "material-section-os-ch03-part1-pcb-threads"),
    "gq-os-ch03-part1-010": ("objective-os-ch03-part1-3", "Time-slice queue trace", "material-section-os-ch03-part1-states-trace"),
    "gq-os-ch03-part2-001": ("objective-os-ch03-part2-1", "Context-switch state save", "material-section-os-ch03-part2-context-browser"),
    "gq-os-ch03-part2-002": ("objective-os-ch03-part2-2", "UNIX exec", "material-section-os-ch03-part2-creation"),
    "gq-os-ch03-part2-003": ("objective-os-ch03-part2-2", "fork return value", "material-section-os-ch03-part2-creation"),
    "gq-os-ch03-part2-004": ("objective-os-ch03-part2-2", "Orphan process", "material-section-os-ch03-part2-termination-ipc"),
    "gq-os-ch03-part2-005": ("objective-os-ch03-part2-3", "Shared-memory performance", "material-section-os-ch03-part2-termination-ipc"),
    "gq-os-ch03-part2-006": ("objective-os-ch03-part2-3", "Bounded-buffer capacity", "material-section-os-ch03-part2-shared-buffer"),
    "gq-os-ch03-part2-007": ("objective-os-ch03-part2-1", "Context-switch overhead", "material-section-os-ch03-part2-context-browser"),
    "gq-os-ch03-part2-008": ("objective-os-ch03-part2-1", "Chrome renderer isolation", "material-section-os-ch03-part2-context-browser"),
    "gq-os-ch03-part2-009": ("objective-os-ch03-part2-3", "Shared-memory synchronization", "material-section-os-ch03-part2-shared-buffer"),
    "gq-os-ch03-part2-010": ("objective-os-ch03-part2-2", "Zombie status retention", "material-section-os-ch03-part2-termination-ipc"),
    "gq-os-ch03-part3-001": ("objective-os-ch03-part3-1", "Message receive primitive", "material-section-os-ch03-part3-message-links"),
    "gq-os-ch03-part3-002": ("objective-os-ch03-part3-2", "Indirect mailbox naming", "material-section-os-ch03-part3-naming-mailboxes"),
    "gq-os-ch03-part3-003": ("objective-os-ch03-part3-2", "Non-blocking send", "material-section-os-ch03-part3-sync-buffering"),
    "gq-os-ch03-part3-004": ("objective-os-ch03-part3-3", "Named-pipe properties", "material-section-os-ch03-part3-pipes"),
    "gq-os-ch03-part3-005": ("objective-os-ch03-part3-3", "UNIX command pipe", "material-section-os-ch03-part3-pipes"),
    "gq-os-ch03-part3-006": ("objective-os-ch03-part3-3", "Socket-pair uniqueness", "material-section-os-ch03-part3-sockets"),
    "gq-os-ch03-part3-007": ("objective-os-ch03-part3-1", "Message-passing address spaces", "material-section-os-ch03-part3-message-links"),
    "gq-os-ch03-part3-008": ("objective-os-ch03-part3-2", "Direct communication link", "material-section-os-ch03-part3-naming-mailboxes"),
    "gq-os-ch03-part3-009": ("objective-os-ch03-part3-2", "Bounded message buffering", "material-section-os-ch03-part3-sync-buffering"),
    "gq-os-ch03-part3-010": ("objective-os-ch03-part3-3", "Ordinary-pipe direction", "material-section-os-ch03-part3-pipes"),
    "gq-os-ch05-part1-001": ("objective-os-ch05-part1-1", "I/O-bound burst distribution", "material-section-os-ch05-part1-foundations"),
    "gq-os-ch05-part1-002": ("objective-os-ch05-part1-2", "Response time", "material-section-os-ch05-part1-criteria"),
    "gq-os-ch05-part1-003": ("objective-os-ch05-part1-1", "Running-to-waiting decision", "material-section-os-ch05-part1-scheduler-dispatcher"),
    "gq-os-ch05-part1-004": ("objective-os-ch05-part1-2", "Dispatcher sequence", "material-section-os-ch05-part1-scheduler-dispatcher"),
    "gq-os-ch05-part1-005": ("objective-os-ch05-part1-3", "FCFS waiting calculation", "material-section-os-ch05-part1-fcfs"),
    "gq-os-ch05-part1-006": ("objective-os-ch05-part1-3", "FCFS convoy effect", "material-section-os-ch05-part1-fcfs"),
    "gq-os-ch05-part1-007": ("objective-os-ch05-part1-1", "CPU-I/O burst cycle", "material-section-os-ch05-part1-foundations"),
    "gq-os-ch05-part1-008": ("objective-os-ch05-part1-1", "Nonpreemptive CPU retention", "material-section-os-ch05-part1-scheduler-dispatcher"),
    "gq-os-ch05-part1-009": ("objective-os-ch05-part1-3", "FCFS FIFO mechanics", "material-section-os-ch05-part1-fcfs"),
    "gq-os-ch05-part1-010": ("objective-os-ch05-part1-1", "Preemption race condition", "material-section-os-ch05-part1-scheduler-dispatcher"),
    "gq-os-ch05-part2-001": ("objective-os-ch05-part2-1", "SJF tie breaking", "material-section-os-ch05-part2-sjf"),
    "gq-os-ch05-part2-002": ("objective-os-ch05-part2-1", "Exponential-average alpha", "material-section-os-ch05-part2-prediction"),
    "gq-os-ch05-part2-003": ("objective-os-ch05-part2-2", "SRTF preemption", "material-section-os-ch05-part2-srtf"),
    "gq-os-ch05-part2-004": ("objective-os-ch05-part2-3", "RR queue rotation", "material-section-os-ch05-part2-rr"),
    "gq-os-ch05-part2-005": ("objective-os-ch05-part2-3", "RR waiting bound", "material-section-os-ch05-part2-rr"),
    "gq-os-ch05-part2-006": ("objective-os-ch05-part2-2", "SJF preemption comparison", "material-section-os-ch05-part2-srtf"),
    "gq-os-ch05-part2-007": ("objective-os-ch05-part2-1", "SJF burst uncertainty", "material-section-os-ch05-part2-sjf"),
    "gq-os-ch05-part2-008": ("objective-os-ch05-part2-1", "SJF optimality", "material-section-os-ch05-part2-sjf"),
    "gq-os-ch05-part2-009": ("objective-os-ch05-part2-3", "RR fairness", "material-section-os-ch05-part2-rr"),
    "gq-os-ch05-part2-010": ("objective-os-ch05-part2-1", "Exponential-average weights", "material-section-os-ch05-part2-prediction"),
    "gq-os-ch05-part3-001": ("objective-os-ch05-part3-1", "Large RR quantum", "material-section-os-ch05-part3-rr-tuning"),
    "gq-os-ch05-part3-002": ("objective-os-ch05-part3-2", "Priority-number convention", "material-section-os-ch05-part3-priority"),
    "gq-os-ch05-part3-003": ("objective-os-ch05-part3-2", "Priority aging", "material-section-os-ch05-part3-priority"),
    "gq-os-ch05-part3-004": ("objective-os-ch05-part3-3", "Per-queue algorithms", "material-section-os-ch05-part3-multilevel"),
    "gq-os-ch05-part3-005": ("objective-os-ch05-part3-3", "Feedback-queue demotion", "material-section-os-ch05-part3-multilevel"),
    "gq-os-ch05-part3-006": ("objective-os-ch05-part3-1", "RR context-switch count", "material-section-os-ch05-part3-rr-tuning"),
    "gq-os-ch05-part3-007": ("objective-os-ch05-part3-1", "Small-quantum overhead", "material-section-os-ch05-part3-rr-tuning"),
    "gq-os-ch05-part3-008": ("objective-os-ch05-part3-1", "RR turnaround calculation", "material-section-os-ch05-part3-rr-tuning"),
    "gq-os-ch05-part3-009": ("objective-os-ch05-part3-3", "Multilevel queue preemption", "material-section-os-ch05-part3-multilevel"),
    "gq-os-ch05-part3-010": ("objective-os-ch05-part3-2", "Feedback trace", "material-section-os-ch05-part3-priority"),
    "gq-os-ch05-part4-001": ("objective-os-ch05-part4-1", "Symmetric multiprocessing", "material-section-os-ch05-part4-multiprocessor"),
    "gq-os-ch05-part4-002": ("objective-os-ch05-part4-2", "Logical processor count", "material-section-os-ch05-part4-multicore"),
    "gq-os-ch05-part4-003": ("objective-os-ch05-part4-2", "Pull migration", "material-section-os-ch05-part4-balance-affinity"),
    "gq-os-ch05-part4-004": ("objective-os-ch05-part4-2", "Hard processor affinity", "material-section-os-ch05-part4-balance-affinity"),
    "gq-os-ch05-part4-005": ("objective-os-ch05-part4-3", "Little's law", "material-section-os-ch05-part4-evaluation"),
    "gq-os-ch05-part4-006": ("objective-os-ch05-part4-3", "Deterministic evaluation", "material-section-os-ch05-part4-evaluation"),
    "gq-os-ch05-part4-007": ("objective-os-ch05-part4-1", "Asymmetric bottleneck", "material-section-os-ch05-part4-multiprocessor"),
    "gq-os-ch05-part4-008": ("objective-os-ch05-part4-2", "Common-queue balancing", "material-section-os-ch05-part4-balance-affinity"),
    "gq-os-ch05-part4-009": ("objective-os-ch05-part4-2", "NUMA memory placement", "material-section-os-ch05-part4-balance-affinity"),
    "gq-os-ch05-part4-010": ("objective-os-ch05-part4-3", "Implementation limits", "material-section-os-ch05-part4-evaluation"),
}

NEW_MCQ_SOURCE_VERIFIED_HASHES = {
    "gq-os-ch03-part1-001": "2aa20ebb6b6143eb4a9d93954cd33d730f81930e1a6b26c59cee3ad5cc67cbe3",
    "gq-os-ch03-part1-002": "dd946a38db289930cb04e0e034bd1d29c6b4b233b9393ce65dc3cff04a18d528",
    "gq-os-ch03-part1-003": "6d81e54fc0937963e3980a78e7e8e3277dbbfab240a53ee5109ae3d1cfde126f",
    "gq-os-ch03-part1-004": "1cdc8fe1a1390154096721625c8979b9c25294961f5dd792621e2d97a82cbf4c",
    "gq-os-ch03-part1-005": "7638935294f319a388b1caa19d6f6f584c094fcf424fd0e4ebab13406cbe66e2",
    "gq-os-ch03-part1-006": "b9cb328f2be3a884a9830fa23e01c4ef90135fb8e35e15115ee4ba48509568d9",
    "gq-os-ch03-part2-001": "f4ec13bd2047bc19c391221e7a7cf1460b581068f463f4ce8702e63aa75ae971",
    "gq-os-ch03-part2-002": "dc93d4211d21ed61219630ce3b16c50d499b8f4fa50ed5902219696f0f90e86e",
    "gq-os-ch03-part2-003": "e0c7e617f444662be08dada51d34cec3ca071efd6de0d984945900376a9af234",
    "gq-os-ch03-part2-004": "411503fcb805eb7befb65682134135b31c18a96c887d749bf94d20225c84dab6",
    "gq-os-ch03-part2-005": "a0844b51ab88bce0c92708c43905fb51b703ccb5bb6df9c939f7994667792d1e",
    "gq-os-ch03-part2-006": "797951fbb8c3d2904078cade1bc8106badaa05b76078fb2110e28e757c77cdf8",
    "gq-os-ch03-part3-001": "3ea60b7fcff9a2deb7767c4f97a7afbb8cca3773beee62551b3f584f4e0360d7",
    "gq-os-ch03-part3-002": "001cc5d624b0b6c7e9a4b0613ac9fc815cdfae444ad5737ea2c8fcd974e81439",
    "gq-os-ch03-part3-003": "8c24e6901df37466661c5b3b3410ec7327d65d56e08142ffc11da707baa04399",
    "gq-os-ch03-part3-004": "fdc9510ed3f3fcbd0e889a4caf27b040b1be9f26ac88c1a50442368011eb438c",
    "gq-os-ch03-part3-005": "36f497265d9d3940c1d265346924f6e02b7d52f6a3fb217b8661386c459de8c5",
    "gq-os-ch03-part3-006": "444662c90885bdcf0c33c32f5ccca3081946df63d48dd5915e879997b40cfd0d",
    "gq-os-ch05-part1-001": "bf4b5f4904b129f1b5e896596ac93f6a966568be8e1009635458480c3f5ad548",
    "gq-os-ch05-part1-002": "c8df4116d1eed43b5f8fa2c8ae3eac1ed4392eb1007da3d291b9a51b4f43e1e9",
    "gq-os-ch05-part1-003": "493e53762c21135b1e8f621d236abc434dd0fb7095294fde7db558eeb75f60fc",
    "gq-os-ch05-part1-004": "9626cda559fa39a86658f3399b88f6bad1f4b6aaad9d08051baa3e230b9634cb",
    "gq-os-ch05-part1-005": "2653b25e2ad1f3e9b1c1a9ed1e13583763ca49c694504c522740ade468ef9e14",
    "gq-os-ch05-part1-006": "2a367b06f0b5b885d986802f80868f62a089fa8f14ede14c960e7f272eeb838f",
    "gq-os-ch05-part2-001": "bdee0ad832473db4f3a1ac5ef4786a379199454d8138da000b04ded11ee16ff7",
    "gq-os-ch05-part2-002": "2d5d5dc18f5e7a3f5a7519d29c59e9ceaab64ba292b2720fade14d9e8a207ba9",
    "gq-os-ch05-part2-003": "5bb07078f3a1fcfbe1226d818272c1f3bef8bb9d9ea5ae531fb8c8307c86fcc8",
    "gq-os-ch05-part2-004": "004b481b83011ca43c9e981a30d03ee32e961a7dc689c1e1adf3744b56618da7",
    "gq-os-ch05-part2-005": "da0eb04f998b2f67345a7c4865cc976a171a6b3db945a942e0ce623a95d1f280",
    "gq-os-ch05-part2-006": "5897b6f0b30f1fbf31318e8c9d2b0df98c9258908f2e1c055a6b404e9b7c3c75",
    "gq-os-ch05-part3-001": "37acef5c5d0c9cf3f45bbd88efc72717ece6366870b1ac3b4ff4705fe3dbab83",
    "gq-os-ch05-part3-002": "0f15d81c6a9d1a818a368b092bf50703cb83c6a34fcd28ac3eba41f9fc93892e",
    "gq-os-ch05-part3-003": "195d6dce21f143fe33acb381dc5c3dd7e907f050791b6bc0af272e9d06dcf40f",
    "gq-os-ch05-part3-004": "088ebb22673ae408ae05186802c9dbc063b1dea90ee7b6262ef63cdb7282d10c",
    "gq-os-ch05-part3-005": "968368f6ce526015769b1c03b72f19fc3f45852366ab4521d0e9c37b371c9872",
    "gq-os-ch05-part3-006": "37a8256906afe551893681eb35ffba6116bb3f0dc89299420deac750cc610ab1",
    "gq-os-ch05-part4-001": "847d4af3943e25959fa51f6e343b509f20ce7e715f227ab57accc74a14894d9b",
    "gq-os-ch05-part4-002": "86fb63b4d73f15937b3e50f507625288ece867bec1bee98ee370bdf4168ca44e",
    "gq-os-ch05-part4-003": "3da4788f866a73b142e0b8f39683732505c7afca938f8bd691c87c0f501adb2a",
    "gq-os-ch05-part4-004": "bd28a72cf638d2bfb45483d678109f384de103a7b4c1e92588abbb820db54370",
    "gq-os-ch05-part4-005": "6d2df871c0404480ecea99afa68eb1f4800ecb5f4d87fb6f557361cf1fd8c001",
    "gq-os-ch05-part4-006": "431a2186f2c54a69b0c6d51c3eef174a80c285b5efcfce1200422559fe3c896f",
}
NEW_ARABIC_EXPLANATION_HASHES = {
    "gq-os-ch03-part1-001": "8337624a94815b42188bb8117006957d20b4475d832c81b706b7bc21b94b72c5",
    "gq-os-ch03-part1-002": "e3fbbc3eec2a6d0903ae724d78a43d8df55c6764ff9decf680fdb56fd72f3154",
    "gq-os-ch03-part1-003": "6eee3db640ced8a06ab606827cdc38f1ee3e8049fea54d5bcb67546d0ed5da52",
    "gq-os-ch03-part1-004": "4b90178517ab59574fb18b11b80e0a5c61857edf8333f79abdae21b24593c389",
    "gq-os-ch03-part1-005": "aa2a0cf0a5155d77b3014f9a9b53f3db4c9ab2d44f3c365e80a1b54d8df41e3a",
    "gq-os-ch03-part1-006": "3632bf7ffcf264bd87ea9efee14af4aa05b15f5eb84c995a1aefafc67b9e087f",
    "gq-os-ch03-part1-007": "6bc8619d00e6230aeef0d725823960edf00def2aa12e63a9a5872a0843653b0d",
    "gq-os-ch03-part1-008": "0fc8aa85fbb797d8c9d080626c18c931e3909f85a57865286928ad7d2416ba65",
    "gq-os-ch03-part1-009": "8515a1ac53aa7729b60d153c14fb8865e787d32dde07729955cec972cd4c3978",
    "gq-os-ch03-part1-010": "2b70a6d1d94789789351283bc35a52f0d7d251276dc084f45acadce8ef6abf45",
    "gq-os-ch03-part2-001": "bc015a369df574f3a69283d0a2fd06dc0d9c42d5788ab18421b8af724452fee4",
    "gq-os-ch03-part2-002": "25bedba78cd24b49137c2c1a308750df0fd8f7a953d05368429673703e481d28",
    "gq-os-ch03-part2-003": "db408382ac198bf62b31596437a79afc2488fe2e72dcc41b68d9544a19d2f795",
    "gq-os-ch03-part2-004": "b6ebb90e54d8ee16dff3f81c76b713543149010af851b5a9a000d001d61fca5c",
    "gq-os-ch03-part2-005": "ebc7249306c1f1838cff18cbfb42d8a50d480baa0d0fecd07ca009d1581e4fa5",
    "gq-os-ch03-part2-006": "56a714891ec6aaa61b9102c0db4f20be5a49cdcf87818d6776eda80773f2f68a",
    "gq-os-ch03-part2-007": "005c08757163b87752209fcbc503bfea9a9c6c3bb180310797024ed5a129cc17",
    "gq-os-ch03-part2-008": "b8eb36f80c333e70ac778e0c2a69b70af06a345faa7392a31bf48d370668eada",
    "gq-os-ch03-part2-009": "0d0f3fda5193c071a71dab965acd188fbe978ccaa26e200c6b887468037b6bd7",
    "gq-os-ch03-part2-010": "2b881ef0e98c25ed2a6d3aeb1fa889426e1db99d0fb43dd3cc11d9a1499b2f43",
    "gq-os-ch03-part3-001": "14b10721d4dd5462566d2cc2e651d97bb5fffe60ecbe86f6504bfb3260c1a2c4",
    "gq-os-ch03-part3-002": "c477c040f63420f3c6181d45669d47fabb2683641c2bd7dd4c16f3e2047cc96a",
    "gq-os-ch03-part3-003": "a251fda68d4a8008de82bdfc4eb677be72b241b753fbc7017576bc7911229eaf",
    "gq-os-ch03-part3-004": "4c3161f051607e08f38a0b74c709a0de0e5768c16326bee073096dd1f0b58739",
    "gq-os-ch03-part3-005": "86a870d52e9b4d8a86378e313cdb34b4d35c54845a3cc3c418af2a48fd4ef38e",
    "gq-os-ch03-part3-006": "269198735e798fff869c93f8fbf2a2b07b5f9ddf62bcd7c0585f5390040131a1",
    "gq-os-ch03-part3-007": "d195a36da86f6ce8a8a1e8ad160c9eefaf0493405439486682a7a3839210da8b",
    "gq-os-ch03-part3-008": "1d170cfdf30f0d949299fd2511cd6b1c0a4fa051a0c04e0020015ed419370e5f",
    "gq-os-ch03-part3-009": "44805440667ee3c1c610e05ecac5e1e290e2416f0a27d896053ce0b3cff71595",
    "gq-os-ch03-part3-010": "849ecfc1e8176e72a0d99a222012b0a4106cb48fcf713cc99b634e341f12d8c2",
    "gq-os-ch05-part1-001": "64737b5e7f5896f48456d1cdfe410ff574aed2e9ac7c70fe105f435eedfef34b",
    "gq-os-ch05-part1-002": "4f28b0cec969bdfc785942a89268eeef5f23ebe379b9a96a3ace09842f9461db",
    "gq-os-ch05-part1-003": "9f7d928e574a7ecd1adbec83dffcb27ac693a8326fe819d7b49f1bf2e0b7d503",
    "gq-os-ch05-part1-004": "4dce4455d33c01222bdb9fd9af92856dbc962e8953d77437d3fcf4feca716d8f",
    "gq-os-ch05-part1-005": "8d10d7e0182ded4fef87c81cdd4434a181e100f13940ae3d7898e8f87ba1d3aa",
    "gq-os-ch05-part1-006": "3b6fdeb2c674475eafa9e3afb5dce673d261f1fa898841e3d348952dbc809166",
    "gq-os-ch05-part1-007": "307aa70181f323add8773fac10c9a2175a8d35fc190a88f275a71a01e17dced0",
    "gq-os-ch05-part1-008": "c819b5fa7c0d54bf0539ac067afc0544e0147fa6e1ad2705de915e884eb77131",
    "gq-os-ch05-part1-009": "3b710cd900af00a23b39a4ad31669b2021d0ee7837d9b01072e28e27716f85af",
    "gq-os-ch05-part1-010": "ecc2709e4aea84c1890a898c0dd3c4c6b9aae16870916a945c901de424d0c59c",
    "gq-os-ch05-part2-001": "95830fa64a481640cd2694cd2d393c49dc71ebd2fff2bf532e8b1ce5a200be76",
    "gq-os-ch05-part2-002": "2e823530f0e0902707b0c148bc2a3b5a1a51daf63f8b3ceb2db8091211a56490",
    "gq-os-ch05-part2-003": "685f1b98262f1297a0e14c83117b6e5af28db96f93cbb930a663a132d4ce35d8",
    "gq-os-ch05-part2-004": "2c9001b34b5c186519524e817a51b91540426c9c1716b46e2f20b76f311dc22c",
    "gq-os-ch05-part2-005": "66c565a25dfdb3e11ee2456521ea01657cb1caff7f82171e7465d2ab1063b7d8",
    "gq-os-ch05-part2-006": "2c26f7233a6457fa63934111e36f7d662a1bba4a72dfd3818d1fc3c0074a5b8e",
    "gq-os-ch05-part2-007": "0e000080df828f772a421a20f4e883b6b4a4b9d53c2bc0da61976022af4b511a",
    "gq-os-ch05-part2-008": "23a94d7e07d75265fb41e749d2555af8a55106a5e4c564c6aa4d2516579f64eb",
    "gq-os-ch05-part2-009": "a53aa7cf02d12c5368f31f290f6e65fbb465c7b5f4237cdd977dc94311cce734",
    "gq-os-ch05-part2-010": "cf3261935ea580d122c7a0ae939557822dae96dfb1799d297db8f4cb9971b12c",
    "gq-os-ch05-part3-001": "39875002e3d3b3a30d33933e2659e8afa8d9dfecffc81afbc2f35a607b36f075",
    "gq-os-ch05-part3-002": "8e22e6804ac2eb65841975a1676b36a460bc13fe77d6ace159395125e0100043",
    "gq-os-ch05-part3-003": "9b87a20ca067dbf574754c25a4ed69bf280d55d1cffc4d60f4bdaa316b27077e",
    "gq-os-ch05-part3-004": "0b37f0a93a168f05720aefd0ce987a9f9400d21430f5d3c54457800c3335f73d",
    "gq-os-ch05-part3-005": "c4715ac4f66bacf84b9386a7c178ba281a2394548e57a75072f29fee3e5cb19d",
    "gq-os-ch05-part3-006": "331db2243c6beb4b036975bfb982b857d0afba915c3c394064b65a634a749627",
    "gq-os-ch05-part3-007": "6896da36e813c9cb72c80dbca4b6109f0af4ac7181e4de0398d01b3aa12ec145",
    "gq-os-ch05-part3-008": "0e7cf53b7f70974446d3045c4da18aec19c84521029126d4d552487029da4e04",
    "gq-os-ch05-part3-009": "a804510a79a17aa5432174d2c9fcb1297f77364ed716cf2f2f0e3beb4252e2e2",
    "gq-os-ch05-part3-010": "debbf463b8d3a55d1a51f3f4423a3300aedd6824d2e3b33dae1f9e284c7deece",
    "gq-os-ch05-part4-001": "37ec3ada63caeebd890be6ec6cab1f8fdec57abd6ea41685c6f83a02eb0c26ba",
    "gq-os-ch05-part4-002": "0d7d56580d61e3c89714e09b1cd9fb13ffdbc93ac91d685838dcd71add68c0cf",
    "gq-os-ch05-part4-003": "28e5cd1ca3a26cbf2b70fe07e30197d4bb8bb38f2320710d9cf46015be681688",
    "gq-os-ch05-part4-004": "8923f2a121d283e8b8479eb178c08047cc5eec0dd5c23f21432b3e4b4cd4b57f",
    "gq-os-ch05-part4-005": "73b1e0352292a5a6e5cb007bacd5dc366cf5c22888dc13aa18287a7acd3f3ec3",
    "gq-os-ch05-part4-006": "cf6912b2fb62e8c2fdf6f82bbbcc65aecc6f24f2c456ba55b806ca481a656ea9",
    "gq-os-ch05-part4-007": "f6cfcc6cef36b9d0f54fbc0034435b9b81f42979d1da602209419fa10389c155",
    "gq-os-ch05-part4-008": "9c19d9be80dd052cb238c6e23fd9d3ae5985b4620c9d7eb35b498cd4e6d8479b",
    "gq-os-ch05-part4-009": "c85b393b5cedc83f77ce36f3188167b3448915499a3fff006ac0d0ded95cb9f2",
    "gq-os-ch05-part4-010": "ad268b9ab789279d9daf80104e2ef84026f0a1fe55d7151860f714930adbd613",
}
NEW_TRUE_FALSE_SOURCE_VERIFIED_HASHES = {
    "gq-os-ch03-part1-007": "8c17f1c7a31d9d3431024dff5f5c0f83b12d60195b792e0c85b17b04e205810b",
    "gq-os-ch03-part1-008": "d78334f548f31275e65dedf07ed5a31d5340e9b7507f9c57477e1ba14fbcc087",
    "gq-os-ch03-part1-009": "c9f953185967c204ee0ea60798631e21172a20f273552bf91a5dcdef20d17753",
    "gq-os-ch03-part1-010": "a7d955df9daf1602a7fe525fa2c54f62d453bae0e673b5286e5d26246b29f896",
    "gq-os-ch03-part2-007": "0d0451a568322229f89bb1f6d00a0ae2db4cd24d7ebf785f9205d5dd2249639b",
    "gq-os-ch03-part2-008": "47b5b2cd0bf29c5945bccea80b00ec4ca5ff269250ab9a61560b683df5695cff",
    "gq-os-ch03-part2-009": "b0944967c4d1fb1ebd28cffdb72f97ea18b984500a76c4db6b73ec4b1098bd80",
    "gq-os-ch03-part2-010": "6404538acab6799e7f2b6b68434ba0cdb3654411b4994aba37401a6492d07665",
    "gq-os-ch03-part3-007": "09f7fead356b61a517a671458b3a87fab5efefcca83201a3b3e211497b955d77",
    "gq-os-ch03-part3-008": "9fc1deed7a252f21ef13085fd1f110e6ce1842239319b90e6560d570befae452",
    "gq-os-ch03-part3-009": "fbd8d50c3edd32d7295091fb09bd6ff1831c4f34a6f03f73b9dbb26874390009",
    "gq-os-ch03-part3-010": "9cc25250651d0573f0f724f8e3a60d43107053667d13a7dfc2f10fa8303dcac7",
    "gq-os-ch05-part1-007": "5e78c26b323cfbd4e0d7a4ec5a35bb140d187ca3d5e932f5fe86343a3959b434",
    "gq-os-ch05-part1-008": "f1b0ba6f87496eef9e08a3ca769cc08554a8fac729621e2496727ef547d4ba81",
    "gq-os-ch05-part1-009": "011a48bce0c30e18785f3a681a98757a808e2c7caf48d08e3843eb0a6a22d1e7",
    "gq-os-ch05-part1-010": "5bc5374778794643338f3c34c8f7e581e553cf14944d554a8725ba0b7cc3ca5a",
    "gq-os-ch05-part2-007": "5df145c72a2c8e289b2027edda0e085ff9e7aa1991a1f5cb4f452ef81d37765d",
    "gq-os-ch05-part2-008": "a6403bcd97f9e301bacfd2973ba829226d0eba04f11f9fc672686c582bd2eb56",
    "gq-os-ch05-part2-009": "ad4e12baa5248c8f25cd9ef1029d5dc739ef8c1a82bbb4c80ea47b99abec77ed",
    "gq-os-ch05-part2-010": "1f23ca8f8d4ca9bcfc3a65a0205d584319dd7bdb82b0681f1ec6a104674fe0d4",
    "gq-os-ch05-part3-007": "7299fc4345b48ab829e36e8adfb59dd205fd5f4abb868ce7cfeaf6be20872313",
    "gq-os-ch05-part3-008": "3c162a151db4772f776876ba7cd513f5446c024a037d332bb09c9b0020358543",
    "gq-os-ch05-part3-009": "91a5fea405b7779ab3694056974eebad5d66af3ad0138b7572c195cbdb1c0709",
    "gq-os-ch05-part3-010": "a0df7a7e96ba4d3fff7189ffec565abbc17a89d8405c98b1ef036bb4bfa54b49",
    "gq-os-ch05-part4-007": "fc7d467bcf22aecf2dc1c8009d2afae1e63b8277bdf57b8a433681c3473895d2",
    "gq-os-ch05-part4-008": "2c62e1b37f22348c4ef5d5c86ff4032455d7791cff6ee69e460813677594c513",
    "gq-os-ch05-part4-009": "362dabd37e97614d95f83e1b38f1996054e2191472eef70b33451c7b3a0eb89f",
    "gq-os-ch05-part4-010": "3e725167d4526161ae94465ae66f7f367d019598a50111d7085f8bf6f838a72f",
}


PART_THREE_MCQ_ANSWER_KEY = {'gq-os-ch06-part1-001': 0,
 'gq-os-ch06-part1-002': 1,
 'gq-os-ch06-part1-003': 2,
 'gq-os-ch06-part1-004': 1,
 'gq-os-ch06-part1-005': 1,
 'gq-os-ch06-part1-006': 2,
 'gq-os-ch06-part2-001': 0,
 'gq-os-ch06-part2-002': 1,
 'gq-os-ch06-part2-003': 2,
 'gq-os-ch06-part2-004': 1,
 'gq-os-ch06-part2-005': 1,
 'gq-os-ch06-part2-006': 2,
 'gq-os-ch08-part1-001': 0,
 'gq-os-ch08-part1-002': 1,
 'gq-os-ch08-part1-003': 2,
 'gq-os-ch08-part1-004': 1,
 'gq-os-ch08-part1-005': 1,
 'gq-os-ch08-part1-006': 2,
 'gq-os-ch08-part2-001': 0,
 'gq-os-ch08-part2-002': 1,
 'gq-os-ch08-part2-003': 1,
 'gq-os-ch08-part2-004': 2,
 'gq-os-ch08-part2-005': 1,
 'gq-os-ch08-part2-006': 1,
 'gq-os-ch08-part3-001': 1,
 'gq-os-ch08-part3-002': 1,
 'gq-os-ch08-part3-003': 2,
 'gq-os-ch08-part3-004': 1,
 'gq-os-ch08-part3-005': 1,
 'gq-os-ch08-part3-006': 2,
 'gq-os-ch09-part1-001': 0,
 'gq-os-ch09-part1-002': 1,
 'gq-os-ch09-part1-003': 2,
 'gq-os-ch09-part1-004': 2,
 'gq-os-ch09-part1-005': 1,
 'gq-os-ch09-part1-006': 2,
 'gq-os-ch09-part2-001': 0,
 'gq-os-ch09-part2-002': 1,
 'gq-os-ch09-part2-003': 1,
 'gq-os-ch09-part2-004': 1,
 'gq-os-ch09-part2-005': 2,
 'gq-os-ch09-part2-006': 2}


PART_THREE_QUESTION_METADATA = {'gq-os-ch06-part1-001': ('objective-os-ch06-part1-1', 'Cooperating-process data sharing', 'material-section-os-ch06-part1-races'),
 'gq-os-ch06-part1-002': ('objective-os-ch06-part1-1', 'Producer-consumer counter initialization', 'material-section-os-ch06-part1-races'),
 'gq-os-ch06-part1-003': ('objective-os-ch06-part1-1', 'Critical-section exclusion', 'material-section-os-ch06-part1-critical-section'),
 'gq-os-ch06-part1-004': ('objective-os-ch06-part1-1', 'Critical-section progress', 'material-section-os-ch06-part1-critical-section'),
 'gq-os-ch06-part1-005': ('objective-os-ch06-part1-2', 'Peterson shared variables', 'material-section-os-ch06-part1-peterson'),
 'gq-os-ch06-part1-006': ('objective-os-ch06-part1-3', 'Reordering diagnosis', 'material-section-os-ch06-part1-reordering'),
 'gq-os-ch06-part1-007': ('objective-os-ch06-part1-1', 'Interrupt disabling scope', 'material-section-os-ch06-part1-critical-section'),
 'gq-os-ch06-part1-008': ('objective-os-ch06-part1-2', 'Peterson scalability', 'material-section-os-ch06-part1-peterson'),
 'gq-os-ch06-part1-009': ('objective-os-ch06-part1-1', 'Counter interleaving trace', 'material-section-os-ch06-part1-races'),
 'gq-os-ch06-part1-010': ('objective-os-ch06-part1-2', 'Peterson entry sequence', 'material-section-os-ch06-part1-peterson'),
 'gq-os-ch06-part2-001': ('objective-os-ch06-part2-1', 'Memory-barrier visibility', 'material-section-os-ch06-part2-hardware'),
 'gq-os-ch06-part2-002': ('objective-os-ch06-part2-1', 'Test-and-set return value', 'material-section-os-ch06-part2-hardware'),
 'gq-os-ch06-part2-003': ('objective-os-ch06-part2-2', 'Mutex spinlock cost', 'material-section-os-ch06-part2-mutex'),
 'gq-os-ch06-part2-004': ('objective-os-ch06-part2-2', 'Semaphore domains', 'material-section-os-ch06-part2-semaphores'),
 'gq-os-ch06-part2-005': ('objective-os-ch06-part2-2', 'Event-order semaphore', 'material-section-os-ch06-part2-semaphores'),
 'gq-os-ch06-part2-006': ('objective-os-ch06-part2-3', 'Bounded-buffer sequence trace', 'material-section-os-ch06-part2-classical'),
 'gq-os-ch06-part2-007': ('objective-os-ch06-part2-1', 'Test-and-set bounded waiting', 'material-section-os-ch06-part2-hardware'),
 'gq-os-ch06-part2-008': ('objective-os-ch06-part2-2', 'Counting resource initialization', 'material-section-os-ch06-part2-semaphores'),
 'gq-os-ch06-part2-009': ('objective-os-ch06-part2-3', 'Priority-inversion diagnosis', 'material-section-os-ch06-part2-semaphores'),
 'gq-os-ch06-part2-010': ('objective-os-ch06-part2-3', 'Incorrect semaphore order', 'material-section-os-ch06-part2-semaphores'),
 'gq-os-ch08-part1-001': ('objective-os-ch08-part1-1', 'No-cycle conclusion', 'material-section-os-ch08-part1-graphs'),
 'gq-os-ch08-part1-002': ('objective-os-ch08-part1-2', 'Deadlock handling choices', 'material-section-os-ch08-part1-handling'),
 'gq-os-ch08-part1-003': ('objective-os-ch08-part1-3', 'Sharable resource exclusion', 'material-section-os-ch08-part1-prevention'),
 'gq-os-ch08-part1-004': ('objective-os-ch08-part1-3', 'Hold-and-wait prevention', 'material-section-os-ch08-part1-prevention'),
 'gq-os-ch08-part1-005': ('objective-os-ch08-part1-3', 'No-preemption limitation', 'material-section-os-ch08-part1-prevention'),
 'gq-os-ch08-part1-006': ('objective-os-ch08-part1-3', 'Resource-order trade-off', 'material-section-os-ch08-part1-ordering'),
 'gq-os-ch08-part1-007': ('objective-os-ch08-part1-2', 'Prevention versus detection', 'material-section-os-ch08-part1-handling'),
 'gq-os-ch08-part1-008': ('objective-os-ch08-part1-3', 'No-preemption release', 'material-section-os-ch08-part1-prevention'),
 'gq-os-ch08-part1-009': ('objective-os-ch08-part1-3', 'Resource-order comparison', 'material-section-os-ch08-part1-ordering'),
 'gq-os-ch08-part1-010': ('objective-os-ch08-part1-2', 'Ignoring deadlocks policy', 'material-section-os-ch08-part1-handling'),
 'gq-os-ch08-part2-001': ('objective-os-ch08-part2-1', 'Avoidance maximum claims', 'material-section-os-ch08-part2-safety'),
 'gq-os-ch08-part2-002': ('objective-os-ch08-part2-1', 'Unsafe-state meaning', 'material-section-os-ch08-part2-safety'),
 'gq-os-ch08-part2-003': ('objective-os-ch08-part2-1', 'Claim-edge transition', 'material-section-os-ch08-part2-rag-avoidance'),
 'gq-os-ch08-part2-004': ('objective-os-ch08-part2-1', 'Single-instance grant check', 'material-section-os-ch08-part2-rag-avoidance'),
 'gq-os-ch08-part2-005': ('objective-os-ch08-part2-2', 'Need computation', 'material-section-os-ch08-part2-banker'),
 'gq-os-ch08-part2-006': ('objective-os-ch08-part2-3', 'Banker vector comparison', 'material-section-os-ch08-part2-banker-example'),
 'gq-os-ch08-part2-007': ('objective-os-ch08-part2-2', 'Banker instance scope', 'material-section-os-ch08-part2-safety'),
 'gq-os-ch08-part2-008': ('objective-os-ch08-part2-2', 'Request-algorithm order', 'material-section-os-ch08-part2-banker'),
 'gq-os-ch08-part2-009': ('objective-os-ch08-part2-3', 'P0 request safety analysis', 'material-section-os-ch08-part2-banker-example'),
 'gq-os-ch08-part2-010': ('objective-os-ch08-part2-3', 'P1 request update', 'material-section-os-ch08-part2-banker-example'),
 'gq-os-ch08-part3-001': ('objective-os-ch08-part3-1', 'Detection-recovery policy', 'material-section-os-ch08-part3-single-instance'),
 'gq-os-ch08-part3-002': ('objective-os-ch08-part3-1', 'Wait-for nodes', 'material-section-os-ch08-part3-single-instance'),
 'gq-os-ch08-part3-003': ('objective-os-ch08-part3-1',
                          'Multiple-instance request matrix',
                          'material-section-os-ch08-part3-multiple-instance'),
 'gq-os-ch08-part3-004': ('objective-os-ch08-part3-1',
                          'Detection Finish initialization',
                          'material-section-os-ch08-part3-multiple-instance'),
 'gq-os-ch08-part3-005': ('objective-os-ch08-part3-1', 'Detection complexity', 'material-section-os-ch08-part3-multiple-instance'),
 'gq-os-ch08-part3-006': ('objective-os-ch08-part3-2', 'P2 request state trace', 'material-section-os-ch08-part3-example-usage'),
 'gq-os-ch08-part3-007': ('objective-os-ch08-part3-3', 'Total rollback', 'material-section-os-ch08-part3-recovery'),
 'gq-os-ch08-part3-008': ('objective-os-ch08-part3-2', 'Detection frequency cost', 'material-section-os-ch08-part3-example-usage'),
 'gq-os-ch08-part3-009': ('objective-os-ch08-part3-3', 'Recovery termination trade-off', 'material-section-os-ch08-part3-recovery'),
 'gq-os-ch08-part3-010': ('objective-os-ch08-part3-3', 'Preemption victim cost', 'material-section-os-ch08-part3-recovery'),
 'gq-os-ch09-part1-001': ('objective-os-ch09-part1-1', 'Direct CPU storage', 'material-section-os-ch09-part1-binding'),
 'gq-os-ch09-part1-002': ('objective-os-ch09-part1-1', 'Base-limit meanings', 'material-section-os-ch09-part1-binding'),
 'gq-os-ch09-part1-003': ('objective-os-ch09-part1-1', 'Address binding stages', 'material-section-os-ch09-part1-binding'),
 'gq-os-ch09-part1-004': ('objective-os-ch09-part1-1', 'Execution-time address spaces', 'material-section-os-ch09-part1-mmu'),
 'gq-os-ch09-part1-005': ('objective-os-ch09-part1-1', 'MMU role', 'material-section-os-ch09-part1-mmu'),
 'gq-os-ch09-part1-006': ('objective-os-ch09-part1-1', 'Dynamic relocation calculation', 'material-section-os-ch09-part1-mmu'),
 'gq-os-ch09-part1-007': ('objective-os-ch09-part1-1', 'Compiler relocation role', 'material-section-os-ch09-part1-binding'),
 'gq-os-ch09-part1-008': ('objective-os-ch09-part1-1', 'Base-limit privilege', 'material-section-os-ch09-part1-binding'),
 'gq-os-ch09-part1-009': ('objective-os-ch09-part1-3', 'External fragmentation diagnosis', 'material-section-os-ch09-part1-fragmentation'),
 'gq-os-ch09-part1-010': ('objective-os-ch09-part1-2', 'Adjacent-hole merging', 'material-section-os-ch09-part1-contiguous'),
 'gq-os-ch09-part2-001': ('objective-os-ch09-part2-1', 'Paging blocks', 'material-section-os-ch09-part2-paging'),
 'gq-os-ch09-part2-002': ('objective-os-ch09-part2-1', 'Paging address fields', 'material-section-os-ch09-part2-paging'),
 'gq-os-ch09-part2-003': ('objective-os-ch09-part2-1', 'PTBR function', 'material-section-os-ch09-part2-tables'),
 'gq-os-ch09-part2-004': ('objective-os-ch09-part2-1', 'Page protection bit', 'material-section-os-ch09-part2-tables'),
 'gq-os-ch09-part2-005': ('objective-os-ch09-part2-1', 'Paging bit calculation', 'material-section-os-ch09-part2-paging'),
 'gq-os-ch09-part2-006': ('objective-os-ch09-part2-1', 'Reentrant-code mapping comparison', 'material-section-os-ch09-part2-tables'),
 'gq-os-ch09-part2-007': ('objective-os-ch09-part2-1', 'Paging fragmentation', 'material-section-os-ch09-part2-paging'),
 'gq-os-ch09-part2-008': ('objective-os-ch09-part2-2', 'Page-out direction', 'material-section-os-ch09-part2-swapping'),
 'gq-os-ch09-part2-009': ('objective-os-ch09-part2-3', 'Virtual address-space comparison', 'material-section-os-ch09-part2-virtual'),
 'gq-os-ch09-part2-010': ('objective-os-ch09-part2-3', 'Page-fault state trace', 'material-section-os-ch09-part2-virtual')}

# Independently transcribed lecture facts. The first field is the reviewed
# correct MCQ index or the reviewed true/false Boolean; it is intentionally
# independent of the authored JSON payload and its hashes.
PART_THREE_MANUAL_SOURCE_FACTS = {
    "gq-os-ch06-part1-001": (0, "os-lec-15", 3, "shared memory"),
    "gq-os-ch06-part1-002": (1, "os-lec-15", 5, "counter"),
    "gq-os-ch06-part1-003": (2, "os-lec-15", 9, "no other process"),
    "gq-os-ch06-part1-004": (1, "os-lec-15", 11, "progress"),
    "gq-os-ch06-part1-005": (1, "os-lec-15", 14, "flag[i]"),
    "gq-os-ch06-part1-006": (2, "os-lec-15", 22, "reordering"),
    "gq-os-ch06-part1-007": (True, "os-lec-15", 12, "interrupts"),
    "gq-os-ch06-part1-008": (False, "os-lec-15", 14, "two processes"),
    "gq-os-ch06-part1-009": (False, "os-lec-15", 7, "counter"),
    "gq-os-ch06-part1-010": (True, "os-lec-15", 15, "turn"),
    "gq-os-ch06-part2-001": (0, "os-lec-16", 4, "memory barrier"),
    "gq-os-ch06-part2-002": (1, "os-lec-16", 7, "original value"),
    "gq-os-ch06-part2-003": (2, "os-lec-16", 13, "spinlock"),
    "gq-os-ch06-part2-004": (1, "os-lec-16", 16, "binary semaphore"),
    "gq-os-ch06-part2-005": (1, "os-lec-16", 17, "synch"),
    "gq-os-ch06-part2-006": (2, "os-lec-16", 22, "signal(full)"),
    "gq-os-ch06-part2-007": (True, "os-lec-16", 8, "bounded waiting"),
    "gq-os-ch06-part2-008": (True, "os-lec-16", 16, "counting semaphore"),
    "gq-os-ch06-part2-009": (False, "os-lec-16", 18, "priority inversion"),
    "gq-os-ch06-part2-010": (False, "os-lec-16", 19, "signal(mutex)"),
    "gq-os-ch08-part1-001": (0, "os-lec-17", 11, "no cycles"),
    "gq-os-ch08-part1-002": (1, "os-lec-17", 12, "detect it, and then recover"),
    "gq-os-ch08-part1-003": (2, "os-lec-17", 14, "read-only"),
    "gq-os-ch08-part1-004": (1, "os-lec-17", 15, "before it begins execution"),
    "gq-os-ch08-part1-005": (1, "os-lec-17", 16, "printers and tape drives"),
    "gq-os-ch08-part1-006": (2, "os-lec-17", 17, "increasing order"),
    "gq-os-ch08-part1-007": (False, "os-lec-17", 12, "prevention"),
    "gq-os-ch08-part1-008": (False, "os-lec-17", 16, "preempted"),
    "gq-os-ch08-part1-009": (True, "os-lec-17", 17, "increasing order"),
    "gq-os-ch08-part1-010": (True, "os-lec-17", 12, "linux"),
    "gq-os-ch08-part2-001": (0, "os-lec-18", 4, "maximum number"),
    "gq-os-ch08-part2-002": (1, "os-lec-18", 6, "unsafe"),
    "gq-os-ch08-part2-003": (1, "os-lec-18", 9, "request edge"),
    "gq-os-ch08-part2-004": (2, "os-lec-18", 10, "cycle"),
    "gq-os-ch08-part2-005": (1, "os-lec-18", 14, "max [i,j]"),
    "gq-os-ch08-part2-006": (1, "os-lec-18", 18, "select p1"),
    "gq-os-ch08-part2-007": (False, "os-lec-18", 8, "single instance of a resource type"),
    "gq-os-ch08-part2-008": (True, "os-lec-18", 16, "need"),
    "gq-os-ch08-part2-009": (False, "os-lec-18", 19, "unsafe"),
    "gq-os-ch08-part2-010": (True, "os-lec-18", 19, "p1 requests"),
    "gq-os-ch08-part3-001": (1, "os-lec-19", 4, "recovery scheme"),
    "gq-os-ch08-part3-002": (1, "os-lec-19", 5, "nodes are processes"),
    "gq-os-ch08-part3-003": (2, "os-lec-19", 7, "k more instances"),
    "gq-os-ch08-part3-004": (1, "os-lec-19", 8, "finish[i] = false"),
    "gq-os-ch08-part3-005": (1, "os-lec-19", 9, "o(m"),
    "gq-os-ch08-part3-006": (2, "os-lec-19", 11, "p1 , p2 , p3 , and p4"),
    "gq-os-ch08-part3-007": (True, "os-lec-19", 18, "total rollback"),
    "gq-os-ch08-part3-008": (True, "os-lec-19", 12, "considerable overhead"),
    "gq-os-ch08-part3-009": (False, "os-lec-19", 15, "one process at a time"),
    "gq-os-ch08-part3-010": (False, "os-lec-19", 18, "minimize cost"),
    "gq-os-ch09-part1-001": (0, "os-lec-20", 3, "registers and main memory"),
    "gq-os-ch09-part1-002": (1, "os-lec-20", 4, "size of the range"),
    "gq-os-ch09-part1-003": (2, "os-lec-20", 8, "must recompile"),
    "gq-os-ch09-part1-004": (2, "os-lec-20", 10, "execution-time"),
    "gq-os-ch09-part1-005": (1, "os-lec-20", 11, "memory-management unit"),
    "gq-os-ch09-part1-006": (2, "os-lec-20", 13, "14346"),
    "gq-os-ch09-part1-007": (False, "os-lec-20", 7, "compiler"),
    "gq-os-ch09-part1-008": (True, "os-lec-20", 5, "privileged"),
    "gq-os-ch09-part1-009": (False, "os-lec-20", 27, "external fragmentation"),
    "gq-os-ch09-part1-010": (True, "os-lec-20", 18, "combined"),
    "gq-os-ch09-part2-001": (0, "os-lec-21", 3, "called frames"),
    "gq-os-ch09-part2-002": (1, "os-lec-21", 4, "page number"),
    "gq-os-ch09-part2-003": (1, "os-lec-21", 10, "base register (ptbr) points"),
    "gq-os-ch09-part2-004": (1, "os-lec-21", 12, "read-only"),
    "gq-os-ch09-part2-005": (2, "os-lec-21", 5, "m = 16 bits"),
    "gq-os-ch09-part2-006": (2, "os-lec-21", 14, "three processes"),
    "gq-os-ch09-part2-007": (False, "os-lec-21", 3, "internal fragmentation"),
    "gq-os-ch09-part2-008": (False, "os-lec-21", 17, "page out"),
    "gq-os-ch09-part2-009": (True, "os-lec-21", 21, "logical address space can therefore be much larger"),
    "gq-os-ch09-part2-010": (True, "os-lec-21", 28, "restart the instruction"),
}

# Manual review page corrections: (source id, required page, rejected prior
# page, source phrase, linked material section). These are intentionally
# separate from authored question/evidence records.
PART_THREE_REVIEWED_PAGE_CORRECTIONS = {
    "gq-os-ch08-part3-007": ("os-lec-19", 18, 17, "total rollback", "material-section-os-ch08-part3-recovery"),
    "gq-os-ch09-part2-009": ("os-lec-21", 21, 20, "logical address space can therefore be much larger", "material-section-os-ch09-part2-virtual"),
    "gq-os-ch08-part2-007": ("os-lec-18", 8, 13, "single instance of a resource type", "material-section-os-ch08-part2-safety"),
}

# Independently reviewed option bindings: (correct index, main-rationale
# anchor, ((exact option, unique category, evidence page, evidence phrase,
# option-rationale anchor), ...)).  The source id comes from the separate
# per-question fact oracle above, so these records cannot be refreshed from
# the authored JSON answer key.
PART_THREE_MCQ_OPTION_ORACLES = {
    "gq-os-ch06-part1-001": (0, "both", (
        ("Both shared memory and message passing", "complete mechanism pair", 3, "shared memory", "complete"),
        ("Shared memory alone", "shared-memory-only", 3, "shared memory", "omits"),
        ("Message passing alone", "message-passing-only", 3, "message passing", "omits"),
        ("Neither shared memory nor message passing", "denial of listed mechanisms", 3, "message passing", "explicitly"),
    )),
    "gq-os-ch06-part1-002": (1, "full-buffer counter", (
        ("One, because a producer is about to run", "premature producer count", 5, "counter", "future producer"),
        ("Zero, because no buffer item is initially full", "initial full-item count", 5, "counter", "correct"),
        ("The buffer capacity, because it counts empty slots", "capacity-for-full-count", 5, "counter", "Capacity"),
        ("Negative one, to reserve the first buffer position", "negative-sentinel invention", 5, "counter", "negative"),
    )),
    "gq-os-ch06-part1-003": (2, "mutual exclusion", (
        ("They may enter when they access different variables", "variable exception", 9, "critical section", "variables"),
        ("They may enter after updating the turn variable", "turn-variable exception", 9, "critical section", "turn"),
        ("None of them may execute a critical section", "mutual-exclusion rule", 9, "no other process", "correct"),
        ("They must first execute their remainder sections", "remainder-section confusion", 9, "critical section", "Remainder"),
    )),
    "gq-os-ch06-part1-004": (1, "indefinite", (
        ("Mutual exclusion", "simultaneous-entry requirement", 11, "progress", "simultaneous"),
        ("Progress", "progress requirement", 11, "progress", "correct"),
        ("Bounded waiting", "requester-wait bound", 11, "progress", "requester"),
        ("The remainder section", "program-section confusion", 11, "progress", "program work"),
    )),
    "gq-os-ch06-part1-005": (1, "ready to enter", (
        ("Pi has completed its remainder section", "post-remainder state", 14, "flag[i]", "remainder"),
        ("Pi is ready to enter its critical section", "entry-interest flag", 14, "flag[i]", "correct"),
        ("Pj is ready to enter its critical section", "wrong-process flag", 14, "flag[i]", "flag[j]"),
        ("Pi has already left its critical section", "post-critical state", 14, "flag[i]", "Leaving"),
    )),
    "gq-os-ch06-part1-006": (2, "both", (
        ("Only Pi can observe its entry condition as true", "Pi-only outcome", 22, "reordering", "not exclusive to Pi"),
        ("Only Pj can observe its entry condition as true", "Pj-only outcome", 22, "reordering", "not exclusive to Pj"),
        ("Both processes can observe conditions that let them enter their critical sections", "simultaneous-entry race", 22, "reordering", "correct"),
        ("Both processes must permanently remain in their remainder sections", "permanent-blocking outcome", 22, "reordering", "permanent"),
    )),
    "gq-os-ch06-part2-001": (0, "loads and stores", (
        ("Earlier loads and stores complete and become visible", "full barrier ordering", 4, "memory barrier", "correct"),
        ("Only earlier stores become visible while earlier loads remain unordered", "stores-only ordering", 4, "memory barrier", "omitting loads"),
        ("Later loads and stores run before earlier memory operations", "reversed ordering", 4, "memory barrier", "prevents"),
        ("All memory operations are removed from the program", "operation-elimination claim", 4, "memory barrier", "does not eliminate"),
    )),
    "gq-os-ch06-part2-002": (1, "original value", (
        ("The value written to the target after the operation", "new-value return", 7, "test_and_set", "newly written"),
        ("The original value of its target", "original-value return", 7, "test_and_set", "correct"),
        ("The target's value only when it was false", "false-only return", 7, "test_and_set", "whether it was false or true"),
        ("The number of processes waiting for the target", "queue-count confusion", 7, "test_and_set", "waiting count"),
    )),
    "gq-os-ch06-part2-003": (2, "loops", (
        ("It swaps the two lock variables on every attempt", "swap-operation confusion", 13, "spinlock", "swapping"),
        ("It places the waiting process into a semaphore queue", "blocking-queue confusion", 13, "spinlock", "busy waiting"),
        ("It continuously loops while the lock is unavailable", "busy-wait loop", 13, "spinlock", "correct"),
        ("It releases the lock before testing it", "pre-test release", 13, "spinlock", "Releasing"),
    )),
    "gq-os-ch06-part2-004": (1, "two values", (
        ("A counting semaphore with any nonnegative integer value", "counting-domain confusion", 16, "binary semaphore", "more than two"),
        ("A binary semaphore with value zero or one", "binary-domain definition", 16, "binary semaphore", "correct"),
        ("A counting semaphore whose value equals the current process identifier", "process-identifier confusion", 16, "binary semaphore", "identifier"),
        ("A binary semaphore whose value equals the buffer capacity", "capacity-as-binary-value", 16, "binary semaphore", "exceed one"),
    )),
    "gq-os-ch06-part2-005": (1, "initializes synch", (
        ("One, so P2 may execute S2 before P1 executes S1", "premature-event permit", 17, "synch", "initial one"),
        ("Zero, so P2 waits until P1 signals after S1", "event-order initialization", 17, "synch", "correct"),
        ("The bounded-buffer capacity, so synch counts empty slots", "buffer-capacity confusion", 17, "synch", "event-order"),
        ("The number of processes, so synch schedules both programs", "scheduler-count confusion", 17, "synch", "scheduler"),
    )),
    "gq-os-ch06-part2-006": (2, "reserves an empty", (
        ("wait(mutex), add item, signal(full), signal(mutex)", "mutex-before-empty", 22, "bounded buffer", "while waiting for space"),
        ("wait(empty), add item, wait(mutex), signal(full)", "unprotected-insertion", 22, "bounded buffer", "before acquiring"),
        ("wait(empty), wait(mutex), add item, signal(mutex), signal(full)", "producer sequence", 22, "bounded buffer", "correct"),
        ("wait(full), wait(mutex), add item, signal(empty), signal(mutex)", "consumer-role reversal", 22, "bounded buffer", "consumer-side"),
    )),
    "gq-os-ch08-part1-001": (0, "no deadlock", (
        ("The system has no deadlock", "no-cycle conclusion", 11, "no cycles", "correct"),
        ("The system is deadlocked but has an unshown cycle", "invented-cycle claim", 11, "no cycles", "cannot be assumed"),
        ("Every resource type is sharable", "resource-property confusion", 11, "no cycles", "Sharability"),
        ("Every process has finished", "completion conclusion", 11, "no cycles", "still execute"),
    )),
    "gq-os-ch08-part1-002": (1, "detection and recovery", (
        ("Prevent deadlock by constraining a necessary condition", "prevention policy", 12, "deadlock prevention", "before deadlock"),
        ("Allow deadlock, then detect it and recover", "detection-recovery policy", 12, "detect it, and then recover", "correct"),
        ("Avoid deadlock by keeping the state safe", "avoidance policy", 12, "deadlock avoidance", "safe"),
        ("Ignore deadlocks and leave handling to developers", "ignore policy", 12, "linux and windows", "separate policy"),
    )),
    "gq-os-ch08-part1-003": (2, "sharable", (
        ("It has no resource instances", "missing-instance claim", 14, "read-only", "not absence"),
        ("It is assigned permanently to one process", "exclusive-assignment claim", 14, "read-only", "opposite"),
        ("It can be shared without exclusive access", "sharable-resource rule", 14, "read-only", "correct"),
        ("It must be requested in increasing numerical order", "ordering-rule confusion", 14, "read-only", "Numerical ordering"),
    )),
    "gq-os-ch08-part1-004": (1, "request and receive", (
        ("Request one resource while retaining previously allocated resources", "retained-resource request", 15, "hold and wait", "exactly"),
        ("Request all needed resources before execution begins", "all-before-execution protocol", 15, "before it begins execution", "correct"),
        ("Request an unavailable resource and keep the resources already held", "hold-and-wait preservation", 15, "hold and wait", "preserves"),
        ("Acquire resources only after the process terminates", "post-termination request", 15, "hold and wait", "no longer needs"),
    )),
    "gq-os-ch08-part1-005": (1, "printers and tape drives", (
        ("CPU registers and memory state", "saveable-state category", 16, "printers and tape drives", "saved and restored"),
        ("Printers and tape drives", "nonpreemptable-device category", 16, "printers and tape drives", "correct"),
        ("Read-only files", "sharable-file category", 16, "printers and tape drives", "sharable"),
        ("Resources whose states can be saved and restored", "restorable-resource contrast", 16, "printers and tape drives", "contrast"),
    )),
    "gq-os-ch08-part1-006": (2, "lower-numbered R4", (
        ("P1 may request R4 because availability alone decides the grant", "availability-only grant", 17, "increasing order", "does not override"),
        ("P1 must request another resource numbered above R5", "rule-direction statement", 17, "increasing order", "direction"),
        ("The request would violate the increasing resource-order requirement", "order-violation diagnosis", 17, "increasing order", "correct"),
        ("P1 must release every resource permanently before any request", "permanent-release claim", 17, "increasing order", "permanently"),
    )),
    "gq-os-ch08-part2-001": (0, "maximum possible demand", (
        ("Its maximum need for each resource type", "maximum-claim declaration", 4, "maximum number", "correct"),
        ("Its current allocation only", "current-allocation-only", 4, "resource-allocation state", "current allocation"),
        ("Its number of available and allocated resources", "current-state confusion", 4, "available and allocated resources", "current state"),
        ("Its maximum demand for only one resource type", "single-resource-type claim", 4, "each type", "incomplete"),
    )),
    "gq-os-ch08-part2-002": (1, "deadlock implies unsafe", (
        ("Every unsafe state is already deadlocked", "unsafe-is-deadlocked", 6, "unsafe", "does not mean deadlock"),
        ("A deadlocked state is unsafe, but an unsafe state may not yet be deadlocked", "deadlock-implies-unsafe", 6, "unsafe", "correct"),
        ("A safe state necessarily contains a circular wait", "safe-circular-wait claim", 6, "safe state", "not its defining"),
        ("An unsafe state has no pending requests", "request-absence claim", 6, "unsafe", "absence of requests"),
    )),
    "gq-os-ch08-part2-003": (1, "request edge", (
        ("A claim edge to a different future claim", "claim-persistence", 9, "claim edge", "does not remain"),
        ("A request edge", "claim-to-request transition", 9, "request edge", "correct"),
        ("An assignment edge before allocation", "premature-assignment edge", 9, "assignment edge", "follows allocation"),
        ("A cycle edge", "cycle-as-edge claim", 9, "claim edge", "graph property"),
    )),
    "gq-os-ch08-part2-004": (2, "would not create a cycle", (
        ("The process has no maximum claim", "no-claim condition", 10, "cycle", "requires claims"),
        ("Every resource type is currently free", "all-free condition", 10, "cycle", "unrelated resources"),
        ("The resulting assignment creates no cycle", "acyclic-grant check", 10, "cycle", "correct"),
        ("All processes have completed", "all-complete condition", 10, "cycle", "individual request"),
    )),
    "gq-os-ch08-part2-005": (1, "Max", (
        ("Available − Request", "available-request formula", 14, "Need", "do not define"),
        ("Max − Allocation", "max-allocation formula", 14, "Max", "correct"),
        ("Allocation + Available", "allocation-available formula", 14, "Need", "does not yield"),
        ("Request − Work", "request-work formula", 14, "Need", "not a term"),
    )),
    "gq-os-ch08-part2-006": (1, "P1", (
        ("P0, because its Need is (7,4,3)", "P0 vector failure", 18, "Work = 3 3 2", "exceeding Work"),
        ("P1, because Need1 = (1,2,2) is no greater than Work = (3,3,2)", "P1 vector comparison", 18, "select p1", "correct"),
        ("P2, because its Need is (6,0,0)", "P2 vector failure", 18, "Work = 3 3 2", "exceeds"),
        ("P4, because its Need is (4,3,1)", "P4 vector failure", 18, "Work = 3 3 2", "exceeds"),
    )),
    "gq-os-ch08-part3-001": (1, "detection", (
        ("A prevention protocol and a maximum-claim declaration", "prevention setup", 4, "detection-and-recovery", "before allowing"),
        ("A detection algorithm and a recovery scheme", "detection-recovery pair", 4, "recovery scheme", "correct"),
        ("An Available vector and a Request matrix", "detection-data-structure pair", 4, "detection algorithm", "data structures"),
        ("A guaranteed safe sequence before every request", "avoidance guarantee", 4, "deadlock avoidance", "avoidance"),
    )),
    "gq-os-ch08-part3-002": (1, "Processes", (
        ("Resource types", "resource-type nodes", 5, "Nodes are processes", "removed"),
        ("Processes", "process nodes", 5, "Nodes are processes", "correct"),
        ("Resource instances", "resource-instance nodes", 5, "Nodes are processes", "rather than"),
        ("Allocation matrix rows", "matrix-row nodes", 5, "wait-for graph", "multiple-instance"),
    )),
    "gq-os-ch08-part3-003": (2, "additional instances", (
        ("Pi has released k instances of Rj", "released-instance meaning", 7, "Request[i][j]", "Release"),
        ("Rj has k total instances", "total-instance meaning", 7, "Request[i][j]", "resource-type property"),
        ("Pi requests k more instances of Rj", "additional-request meaning", 7, "requesting k more", "correct"),
        ("Pi has completed k requests", "completed-request count", 7, "Request[i][j]", "Finish"),
    )),
    "gq-os-ch08-part3-004": (1, "Finish", (
        ("True, because the process already holds resources", "true-for-held-resources", 8, "Finish[i] = false", "not true"),
        ("False, because a nonzero Allocation starts unfinished", "false-for-nonzero-allocation", 8, "Finish[i] = false", "correct"),
        ("Equal to Work, because Work contains available resources", "work-as-boolean", 8, "Work = Available", "not a Boolean"),
        ("Equal to Request, because Request is the remaining demand", "request-as-boolean", 8, "Finish[i]", "not assigned"),
    )),
    "gq-os-ch08-part3-005": (1, "O(m × n²)", (
        ("O(n) operations", "linear-complexity claim", 9, "O(m x n2)", "not linear"),
        ("O(m × n²) operations", "detection-complexity bound", 9, "O(m x n2)", "correct"),
        ("O(2^m) operations", "exponential-complexity claim", 9, "O(m x n2)", "not exponential"),
        ("O(log n) operations", "logarithmic-complexity claim", 9, "O(m x n2)", "logarithmic"),
    )),
    "gq-os-ch08-part3-006": (2, "leaving P1 through P4", (
        ("Only P0 is deadlocked", "P0-only deadlock", 11, "deadlock exists", "not one"),
        ("The system remains safe because one C is requested", "safe-state claim", 11, "now deadlocked", "not safe"),
        ("P1, P2, P3, and P4 are deadlocked", "remaining deadlocked set", 11, "p1 , p2 , p3 , and p4", "correct"),
        ("Every process terminates automatically", "automatic-termination claim", 11, "deadlock exists", "does not automatically"),
    )),
    "gq-os-ch09-part1-001": (0, "registers and main memory", (
        ("Registers and main memory", "direct-storage pair", 3, "main memory and registers", "correct"),
        ("Cache and main memory", "cache-for-registers", 3, "cache", "direct general-purpose"),
        ("Disk storage and registers", "disk-for-memory", 3, "from disk", "moved into main memory"),
        ("Program files and cache", "non-direct program-cache pair", 3, "program", "not the two"),
    )),
    "gq-os-ch09-part1-002": (1, "limit", (
        ("The smallest legal physical address", "base-register meaning", 4, "base register holds", "base register"),
        ("The size of the legal address range", "limit-register meaning", 4, "limit register specifies", "correct"),
        ("The maximum legal physical address", "upper-bound confusion", 4, "size of the range", "not the maximum"),
        ("The base address of the user process", "base-address confusion", 4, "base register", "base register"),
    )),
    "gq-os-ch09-part1-003": (2, "recompilation", (
        ("Execution time", "execution-binding stage", 8, "execution time", "hardware address mapping"),
        ("Load time", "load-binding stage", 8, "load time", "reload"),
        ("Compile time", "compile-binding stage", 8, "recompile code", "correct"),
        ("Run time after a page fault", "page-fault-stage confusion", 8, "address binding", "not one"),
    )),
    "gq-os-ch09-part1-004": (2, "execution-time", (
        ("During compile-time binding", "compile-time equality", 10, "execution-time", "same"),
        ("During load-time binding", "load-time equality", 10, "execution-time", "same"),
        ("During execution-time binding", "execution-time difference", 10, "execution-time", "correct"),
        ("Only when a page is read-only", "protection-condition confusion", 10, "logical addresses", "unrelated"),
    )),
    "gq-os-ch09-part1-005": (1, "memory-management unit", (
        ("The relocation register", "relocation-register-versus-device", 11, "memory-management unit", "supplies a value"),
        ("The memory-management unit", "MMU role", 11, "memory-management unit", "correct"),
        ("The base register", "base-register-versus-device", 11, "memory-management unit", "input"),
        ("The user process", "process-versus-MMU", 11, "logical addresses", "generates"),
    )),
    "gq-os-ch09-part1-006": (2, "14346", (
        ("346", "logical-address value", 13, "location 346", "logical"),
        ("14000", "relocation-base value", 13, "base is at 14000", "base value"),
        ("14346", "relocation-sum result", 13, "mapped to location 14346", "correct"),
        ("420939", "unrelated-limit result", 13, "14000", "separate"),
    )),
    "gq-os-ch09-part2-001": (0, "frames", (
        ("Frames", "paging-frame name", 3, "called frames", "correct"),
        ("Pages", "logical-page confusion", 3, "logical memory", "logical-memory"),
        ("Page-table entries", "page-table-entry confusion", 3, "page table", "record translations"),
        ("Fixed-sized blocks of backing store", "backing-store-block confusion", 3, "Backing store", "not the physical"),
    )),
    "gq-os-ch09-part2-002": (1, "page number", (
        ("Page offset", "offset-field confusion", 4, "page number", "within a page"),
        ("Page number", "page-table index", 4, "page number", "correct"),
        ("Frame number", "translated-frame confusion", 4, "page number", "obtained"),
        ("Protection bit", "protection-bit confusion", 4, "page number", "not the"),
    )),
    "gq-os-ch09-part2-003": (1, "page table", (
        ("The page-table length register (PTLR)", "PTLR-versus-PTBR", 10, "ptlr", "different register"),
        ("The page table", "PTBR table pointer", 10, "ptbr) points to the page table", "correct"),
        ("The backing-store location of the current page", "backing-store pointer", 10, "page table", "not the table"),
        ("The translation look-aside buffer entry", "TLB-entry pointer", 10, "translation look-aside", "single cache entry"),
    )),
    "gq-os-ch09-part2-004": (1, "read-only", (
        ("Whether the frame is shared by several processes", "sharing attribute", 12, "protection bit", "separate"),
        ("Whether access is read-only or read-write", "access permission", 12, "read-only", "correct"),
        ("Whether the page number is zero", "address-field confusion", 12, "protection bit", "address field"),
        ("Whether the page is in backing store", "validity-bit confusion", 12, "valid-invalid bit", "valid-invalid"),
    )),
    "gq-os-ch09-part2-005": (2, "Sixteen", (
        ("Ten logical-address bits", "page-size-only count", 5, "1024", "only 1024"),
        ("Fifteen logical-address bits", "one-factor-short count", 5, "64 pages", "one factor"),
        ("Sixteen logical-address bits", "logical-address calculation", 5, "m = 16 bits", "correct"),
        ("Twenty logical-address bits", "different-example count", 5, "16 bits", "different"),
    )),
    "gq-os-ch09-part2-006": (2, "one physical copy", (
        ("Give each process a separate writable libc copy", "private-writable copies", 14, "same physical copy", "discard"),
        ("Map the libc code once into one process only", "one-process-only mapping", 14, "three processes", "three processes"),
        ("Map the same read-only reentrant libc copy into all three processes", "shared-reentrant mapping", 14, "same physical copy", "correct"),
        ("Store the libc code only in backing store", "backing-store-only mapping", 14, "physical copy", "not the executing"),
    )),
}

# Independently reviewed true/false answer and correction bindings:
# (Boolean answer, rationale anchor, correction anchor or None).
PART_THREE_TRUE_FALSE_ORACLES = {
    "gq-os-ch06-part1-007": (True, "one core", None),
    "gq-os-ch06-part1-008": (False, "two processes", "restricted to two processes"),
    "gq-os-ch06-part1-009": (False, "four, five, and six", "four, five, and six"),
    "gq-os-ch06-part1-010": (True, "Pi's interest", None),
    "gq-os-ch06-part2-007": (True, "wait indefinitely", None),
    "gq-os-ch06-part2-008": (True, "available instances", None),
    "gq-os-ch06-part2-009": (False, "lower-priority", "lower-priority"),
    "gq-os-ch06-part2-010": (False, "multiple processes", "multiple processes"),
    "gq-os-ch08-part1-007": (False, "never enters", "never enters"),
    "gq-os-ch08-part1-008": (False, "preempts", "preempts"),
    "gq-os-ch08-part1-009": (True, "increasing ordering", None),
    "gq-os-ch08-part1-010": (True, "Linux and Windows", None),
    "gq-os-ch08-part2-007": (False, "multiple resource instances", "multiple resource instances"),
    "gq-os-ch08-part2-008": (True, "Request less than or equal to Need", None),
    "gq-os-ch08-part2-009": (False, "unsafe", "unsafe"),
    "gq-os-ch08-part2-010": (True, "Allocation, Need, and Available", None),
    "gq-os-ch08-part3-007": (True, "aborting the process", None),
    "gq-os-ch08-part3-008": (True, "overhead", None),
    "gq-os-ch08-part3-009": (False, "abort-one-at-a-time", "abort-one-at-a-time"),
    "gq-os-ch08-part3-010": (False, "minimize cost", "minimize cost"),
    "gq-os-ch09-part1-007": (False, "compiler", "compiler"),
    "gq-os-ch09-part1-008": (True, "kernel-mode privileged", None),
    "gq-os-ch09-part1-009": (False, "external fragmentation", "external fragmentation"),
    "gq-os-ch09-part1-010": (True, "merges adjacent", None),
    "gq-os-ch09-part2-007": (False, "internal fragmentation", "internal fragmentation"),
    "gq-os-ch09-part2-008": (False, "memory to backing store", "memory to backing store"),
    "gq-os-ch09-part2-009": (True, "larger than physical memory", None),
    "gq-os-ch09-part2-010": (True, "valid page", None),
}

# Independently transcribed source propositions for all true/false records:
# (full statement clauses, rationale clauses, correction clauses or None).
# Each ordered clause set captures the actor, condition, relation, and result,
# so a new unrelated sentence cannot retain a short anchor and pass.
PART_THREE_TRUE_FALSE_PROPOSITION_ORACLES = {
    "gq-os-ch06-part1-007": (
        ("disabling interrupts", "shared-variable update", "prevent preemption", "single-core system"),
        ("preventing interrupts", "shared-variable instruction sequence", "without preemption", "one core"), None,
    ),
    "gq-os-ch06-part1-008": (
        ("Peterson", "scalable protocol", "arbitrary number of processes"),
        ("Peterson", "restricted to two processes"), ("Peterson", "restricted to two processes"),
    ),
    "gq-os-ch06-part1-009": (
        ("counter starts at five", "producer increment and consumer decrement", "instructions interleave", "guaranteed to remain five", "regardless of the order"),
        ("possible final values four five and six", "only separate execution guarantees five"), ("possible final values four five and six", "only separate execution guarantees five"),
    ),
    "gq-os-ch06-part1-010": (
        ("Pi sets its interest true", "gives turn to the other process", "performs the busy-wait test"),
        ("records Pi", "gives the other process turn", "evaluates the busy-wait condition"), None,
    ),
    "gq-os-ch06-part2-007": (
        ("test_and_set lock", "guarantees mutual exclusion and progress", "does not guarantee bounded waiting"),
        ("no queue is maintained", "wait indefinitely", "exclusion and progress hold"), None,
    ),
    "gq-os-ch06-part2-008": (
        ("counting semaphore", "finite set of resources", "number of available resource instances"),
        ("number of available instances", "decreases on wait", "increases on signal"), None,
    ),
    "gq-os-ch06-part2-009": (
        ("higher-priority process is blocked", "it holds a lock needed by a lower-priority process", "priority inversion"),
        ("lower-priority process holds a lock needed by a higher-priority process",), ("lower-priority process holds a lock needed by a higher-priority process",),
    ),
    "gq-os-ch06-part2-010": (
        ("signal mutex", "before wait mutex", "safe replacement", "critical-section semaphore order"),
        ("incorrect order", "multiple processes into the critical section"), ("incorrect order", "multiple processes into the critical section"),
    ),
    "gq-os-ch08-part1-007": (
        ("deadlock prevention", "deliberately lets the system enter", "deadlock state", "without intervening"),
        ("prevention", "never enters a deadlock state", "permitting one contradicts"), ("deadlock prevention", "never enters a deadlock state"),
    ),
    "gq-os-ch08-part1-008": (
        ("no-preemption prevention protocol", "holding resources", "unavailable resource", "keeps all held resources while waiting"),
        ("preempts the currently held resources", "process waiting list"), ("preempts the currently held resources", "process waiting list"),
    ),
    "gq-os-ch08-part1-009": (
        ("resource has a unique number", "acquire resources in increasing order", "prevents circular wait", "no request can reverse the ordering"),
        ("total increasing ordering", "prevent circular wait"), None,
    ),
    "gq-os-ch08-part1-010": (
        ("Linux and Windows", "ignore deadlocks", "kernel and application developers"),
        ("ignoring deadlocks", "Linux and Windows", "handling left to developers"), None,
    ),
    "gq-os-ch08-part2-007": (
        ("Banker", "deadlock-avoidance algorithm", "every resource type has one instance"),
        ("multiple resource instances", "graph scheme", "single instance per type"), ("multiple resource instances", "graph scheme", "single instance per type"),
    ),
    "gq-os-ch08-part2-008": (
        ("Banker resource request", "checked against Need", "before", "checked against Available"),
        ("Request less than or equal to Need", "then", "Request less than or equal to Available"), None,
    ),
    "gq-os-ch08-part2-009": (
        ("P0", "request 0 2 0", "granted merely because resources are available", "tentative allocation state is unsafe"),
        ("P0", "not granted", "resources are available", "resulting state is unsafe"), ("P0", "not granted", "resources are available", "resulting state is unsafe"),
    ),
    "gq-os-ch08-part2-010": (
        ("P1 receives request 1 0 2", "Allocation becomes 3 0 2", "Need becomes 0 2 0", "Available becomes 2 3 0"),
        ("Allocation Need and Available values", "granting P1", "request"), None,
    ),
    "gq-os-ch08-part3-007": (
        ("determining a safe state is difficult", "resource-preemption recovery", "total rollback", "aborts and restarts the process"),
        ("total rollback", "aborting the process", "restarting it", "safe state is difficult"), None,
    ),
    "gq-os-ch08-part3-008": (
        ("deadlock detection", "every resource request", "cannot be granted immediately", "considerable computation overhead"),
        ("overhead", "extreme detection frequency"), None,
    ),
    "gq-os-ch08-part3-009": (
        ("detection confirms a deadlock", "abort every deadlocked process at once", "rather than aborting one process at a time"),
        ("abort-all", "abort-one-at-a-time", "process termination"), ("abort-all", "abort-one-at-a-time", "process termination"),
    ),
    "gq-os-ch08-part3-010": (
        ("resource-preemption victim", "maximize the cost", "selected process", "ensure fairness"),
        ("minimize cost", "rollback count", "avoid starvation"), ("minimize cost", "rollback count", "avoid starvation"),
    ),
    "gq-os-ch09-part1-007": (
        ("linker rather than the compiler", "symbolic source-code addresses", "relocatable addresses"),
        ("symbolic-to-relocatable binding", "compiler", "linker or loader", "relocatable addresses to absolute addresses"), ("symbolic-to-relocatable binding", "compiler", "linker or loader", "relocatable addresses to absolute addresses"),
    ),
    "gq-os-ch09-part1-008": (
        ("only the operating system", "load base and limit registers", "load instructions are privileged"),
        ("loading these protection registers", "kernel-mode privileged operation"), None,
    ),
    "gq-os-ch09-part1-009": (
        ("enough total memory space", "split into noncontiguous holes", "internal fragmentation"),
        ("not contiguous", "external fragmentation", "unused space", "allocated partition"), ("not contiguous", "external fragmentation", "unused space", "allocated partition"),
    ),
    "gq-os-ch09-part1-010": (
        ("process exits a variable partition", "adjacent free partitions", "combined", "one larger hole"),
        ("multiple-partition allocation", "merges adjacent free partitions", "process exits"), None,
    ),
    "gq-os-ch09-part2-007": (
        ("Paging eliminates both external fragmentation and internal fragmentation", "every frame has a fixed size"),
        ("avoids external fragmentation", "still has internal fragmentation"), ("avoids external fragmentation", "still has internal fragmentation"),
    ),
    "gq-os-ch09-part2-008": (
        ("page out", "backing store into main memory", "page in", "back to disk"),
        ("Page out moves memory to backing store", "page in is the reverse operation"), ("Page out moves memory to backing store", "page in is the reverse operation"),
    ),
    "gq-os-ch09-part2-009": (
        ("logical address space larger than", "installed physical memory", "virtual memory", "larger logical space"),
        ("logical address space larger than physical memory", "key benefit of virtual memory"), None,
    ),
    "gq-os-ch09-part2-010": (
        ("valid reference faults", "page is not in memory", "free frame is found", "brings the page in", "valid-invalid bit v", "restarts the faulting instruction"),
        ("page-fault handling steps", "valid page", "merely not resident"), None,
    ),
}

PART_THREE_ARABIC_TRANSLATION_ANCHORS = {
    "gq-os-ch06-part1-001": ("العمليات المتعاونة", "الذاكرة المشتركة"),
    "gq-os-ch06-part1-002": ("المنتج", "العناصر الممتلئة"),
    "gq-os-ch06-part1-003": ("حرج", "العمليات الأخرى"),
    "gq-os-ch06-part1-004": ("اختيار العملية", "القسم الحرج"),
    "gq-os-ch06-part1-005": ("Peterson", "flag"),
    "gq-os-ch06-part1-006": ("interest", "turn"),
    "gq-os-ch06-part1-007": ("تعطيل المقاطعات", "أحادي النواة"),
    "gq-os-ch06-part1-008": ("Peterson", "اعتباطي"),
    "gq-os-ch06-part1-009": ("counter", "5"),
    "gq-os-ch06-part1-010": ("Peterson", "turn"),
    "gq-os-ch06-part2-001": ("حاجز الذاكرة", "load"),
    "gq-os-ch06-part2-002": ("test_and_set", "القيمة"),
    "gq-os-ch06-part2-003": ("mutex", "spinlock"),
    "gq-os-ch06-part2-004": ("semaphores", "0"),
    "gq-os-ch06-part2-005": ("S1", "S2"),
    "gq-os-ch06-part2-006": ("bounded buffer", "signal"),
    "gq-os-ch06-part2-007": ("test_and_set", "bounded waiting"),
    "gq-os-ch06-part2-008": ("counting semaphore", "الموارد"),
    "gq-os-ch06-part2-009": ("priority inversion", "القفل"),
    "gq-os-ch06-part2-010": ("signal(mutex)", "wait(mutex)"),
    "gq-os-ch08-part1-001": ("resource-allocation graph", "دورة"),
    "gq-os-ch08-part1-002": ("deadlock", "recovery"),
    "gq-os-ch08-part1-003": ("read-only file", "حصري"),
    "gq-os-ch08-part1-004": ("hold and wait", "قبل"),
    "gq-os-ch08-part1-005": ("printers", "tape drives"),
    "gq-os-ch08-part1-006": ("P1", "R5"),
    "gq-os-ch08-part1-007": ("prevention", "detection"),
    "gq-os-ch08-part1-008": ("no-preemption", "الموارد"),
    "gq-os-ch08-part1-009": ("ترتيب", "circular wait"),
    "gq-os-ch08-part1-010": ("Linux", "Windows"),
    "gq-os-ch08-part2-001": ("أقصى", "المورد"),
    "gq-os-ch08-part2-002": ("unsafe", "deadlocked"),
    "gq-os-ch08-part2-003": ("claim edge", "request edge"),
    "gq-os-ch08-part2-004": ("نسخة", "دورة"),
    "gq-os-ch08-part2-005": ("Need", "Max"),
    "gq-os-ch08-part2-006": ("Work", "P1"),
    "gq-os-ch08-part2-007": ("Banker", "نسخ"),
    "gq-os-ch08-part2-008": ("Need", "Available"),
    "gq-os-ch08-part2-009": ("P0", "(0,2,0)"),
    "gq-os-ch08-part2-010": ("P1", "(1,0,2)"),
    "gq-os-ch08-part3-001": ("prevention", "recovery"),
    "gq-os-ch08-part3-002": ("wait-for graph", "العمليات"),
    "gq-os-ch08-part3-003": ("Request[i][j]", "Rj"),
    "gq-os-ch08-part3-004": ("Finish[i]", "Allocationi"),
    "gq-os-ch08-part3-005": ("O(m", "خوارزمية"),
    "gq-os-ch08-part3-006": ("P2", "C"),
    "gq-os-ch08-part3-007": ("total rollback", "safe state"),
    "gq-os-ch08-part3-008": ("deadlock detection", "overhead"),
    "gq-os-ch08-part3-009": ("deadlock", "عملية واحدة"),
    "gq-os-ch08-part3-010": ("resource preemption", "كلفة"),
    "gq-os-ch09-part1-001": ("CPU", "registers"),
    "gq-os-ch09-part1-002": ("limit", "base"),
    "gq-os-ch09-part1-003": ("address binding", "إعادة ترجمة"),
    "gq-os-ch09-part1-004": ("logical", "physical"),
    "gq-os-ch09-part1-005": ("MMU", "logical"),
    "gq-os-ch09-part1-006": ("14000", "14346"),
    "gq-os-ch09-part1-007": ("linker", "compiler"),
    "gq-os-ch09-part1-008": ("base", "privileged"),
    "gq-os-ch09-part1-009": ("holes", "internal fragmentation"),
    "gq-os-ch09-part1-010": ("variable partition", "hole"),
    "gq-os-ch09-part2-001": ("physical memory", "frames"),
    "gq-os-ch09-part2-002": ("logical address", "page table"),
    "gq-os-ch09-part2-003": ("PTBR", "page table"),
    "gq-os-ch09-part2-004": ("protection bit", "read-only"),
    "gq-os-ch09-part2-005": ("64", "1024"),
    "gq-os-ch09-part2-006": ("ثلاث", "libc"),
    "gq-os-ch09-part2-007": ("paging", "internal fragmentation"),
    "gq-os-ch09-part2-008": ("page out", "page in"),
    "gq-os-ch09-part2-009": ("virtual memory", "physical memory"),
    "gq-os-ch09-part2-010": ("page fault", "valid-invalid"),
}

class OSContentPartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extraction = json.loads(EXTRACTION_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def load_part(self, relative_path):
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    def existing_parts(self):
        content_dir = ROOT / "content" / "os"
        if not content_dir.exists():
            return []
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(content_dir.glob("*.json"))]

    def combined_part(self):
        parts = self.existing_parts()
        return {
            "version": "1.0",
            "modules": [item for part in parts for item in part["modules"]],
            "lessons": [item for part in parts for item in part["lessons"]],
            "questions": [item for part in parts for item in part["questions"]],
            "explanations": [item for part in parts for item in part["explanations"]],
        }

    def assert_all_teaching_pages_covered(self, part, source_ids):
        expected = {
            (page["sourceId"], page["page"])
            for page in self.extraction["pages"]
            if page["sourceId"] in source_ids and page["classification"] == "teaching"
        }
        actual = {
            (ref["sourceId"], ref["location"])
            for lesson in part["lessons"]
            for section in lesson["materialSections"]
            for ref in section["sourceRefs"]
            if ref["sourceId"] in source_ids and ref["locationType"] == "page"
        }
        self.assertEqual(actual, expected)

    def iter_source_refs(self, value):
        if isinstance(value, dict):
            if {"sourceId", "locationType", "location"}.issubset(value):
                yield value
            for child in value.values():
                yield from self.iter_source_refs(child)
        elif isinstance(value, list):
            for child in value:
                yield from self.iter_source_refs(child)

    def normalized_prompt(self, value):
        value = unicodedata.normalize("NFKC", value).strip().casefold()
        value = "".join(character if not unicodedata.category(character).startswith("P") else " " for character in value)
        return re.sub(r"\s+", " ", value).strip()

    def questions_for_lesson(self, part, lesson_id):
        prefix = lesson_id.replace("lesson-", "gq-") + "-"
        return [question for question in part["questions"] if question["id"].startswith(prefix)]

    def content_tokens(self, value, stop_words):
        tokens = set()
        for token in re.findall(r"[a-z0-9]+", value.casefold()):
            if (len(token) > 1 or token.isdigit()) and token not in stop_words:
                if len(token) > 4 and token.endswith("ies"):
                    token = token[:-3] + "y"
                elif len(token) > 3 and token.endswith("s"):
                    token = token[:-1]
                tokens.add(token)
        return tokens

    def proposition_tokens(self, question):
        value = question["prompt"] + " " + question["rationale"]
        if question["type"] == "mcq":
            value += " " + question["options"][question["correctAnswer"]]
        elif question["correctedStatement"]:
            value += " " + question["correctedStatement"]
        return self.content_tokens(value, SEMANTIC_STOP_WORDS)

    def part_three_true_false_matches_oracle(self, question):
        """Match all independently transcribed T/F semantics and evidence relations."""
        expected_truth, rationale_anchor, correction_anchor = PART_THREE_TRUE_FALSE_ORACLES[question["id"]]
        statement_clauses, rationale_clauses, correction_clauses = PART_THREE_TRUE_FALSE_PROPOSITION_ORACLES[question["id"]]
        manual_truth, source_id, source_page, _ = PART_THREE_MANUAL_SOURCE_FACTS[question["id"]]

        def has_ordered_clauses(value, clauses):
            value = self.normalized_prompt(value)
            start = 0
            for clause in clauses:
                position = value.find(self.normalized_prompt(clause), start)
                if position < 0:
                    return False
                start = position + 1
            return True

        expected_ref = (source_id, source_page)
        if question["correctAnswer"] != expected_truth or manual_truth != expected_truth:
            return False
        if not has_ordered_clauses(question["prompt"], statement_clauses):
            return False
        if not has_ordered_clauses(question["rationale"], rationale_clauses):
            return False
        if rationale_anchor.casefold() not in question["rationale"].casefold():
            return False

        expected_supports = {
            "prompt": "direct",
            "correctAnswer": "derived",
            "rationale": "derived",
        }
        if expected_truth:
            if question["correctedStatement"] is not None or correction_anchor is not None or correction_clauses is not None:
                return False
        else:
            expected_supports["correctedStatement"] = "derived"
            if question["correctedStatement"] is None or correction_anchor is None or correction_clauses is None:
                return False
            if not has_ordered_clauses(question["correctedStatement"], correction_clauses):
                return False
            if correction_anchor.casefold() not in question["correctedStatement"].casefold():
                return False

        for target, expected_support in expected_supports.items():
            claims = [claim for claim in question["evidenceMap"] if claim["target"] == target]
            if len(claims) != 1 or claims[0]["support"] != expected_support:
                return False
            claim_refs = {(ref["sourceId"], ref["location"]) for ref in claims[0]["sourceRefs"]}
            if claim_refs != {expected_ref}:
                return False
        return True

    def test_chapters_one_and_two_have_seven_traceable_lessons(self):
        part = self.load_part("content/os/ch01-ch02.json")
        self.assertEqual([module["id"] for module in part["modules"]], ["module-os-ch01", "module-os-ch02"])
        expected_lessons = [
            ("lesson-os-ch01-part1", "os-lec-01"),
            ("lesson-os-ch01-part2", "os-lec-02"),
            ("lesson-os-ch01-part3", "os-lec-03"),
            ("lesson-os-ch01-part4", "os-lec-04"),
            ("lesson-os-ch02-part1", "os-lec-05"),
            ("lesson-os-ch02-part2", "os-lec-06"),
            ("lesson-os-ch02-part3", "os-lec-07"),
        ]
        self.assertEqual([lesson["id"] for lesson in part["lessons"]], [item[0] for item in expected_lessons])
        for lesson, (_, source_id) in zip(part["lessons"], expected_lessons):
            lesson_source_ids = {
                source_ref["sourceId"]
                for source_ref in self.iter_source_refs(lesson)
            }
            self.assertEqual(lesson_source_ids, {source_id})
        self.assert_all_teaching_pages_covered(part, {f"os-lec-{n:02d}" for n in range(1, 8)})

    def test_chapters_three_and_five_have_seven_traceable_lessons(self):
        part = self.load_part("content/os/ch03-ch05.json")
        self.assertEqual([module["id"] for module in part["modules"]], ["module-os-ch03", "module-os-ch05"])
        self.assertEqual([module["order"] for module in part["modules"]], [3, 4])
        self.assertEqual(len(part["lessons"]), 7)
        self.assert_all_teaching_pages_covered(part, {f"os-lec-{n:02d}" for n in range(8, 15)})

    def test_chapters_six_eight_and_nine_have_seven_traceable_lessons(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        self.assertEqual(
            [module["id"] for module in part["modules"]],
            ["module-os-ch06", "module-os-ch08", "module-os-ch09"],
        )
        self.assertEqual([module["order"] for module in part["modules"]], [5, 6, 7])
        self.assertEqual(len(part["lessons"]), 7)
        self.assert_all_teaching_pages_covered(part, {f"os-lec-{n:02d}" for n in range(15, 22)})

    def test_every_generated_question_has_separate_arabic_guidance(self):
        part = self.combined_part()
        explanations = {item["questionId"]: item for item in part["explanations"]}
        self.assertEqual(len(part["questions"]), 210)
        for question in part["questions"]:
            self.assertEqual(question["origin"], "generated")
            self.assertIn(question["id"], explanations)
            self.assertIn(len(explanations[question["id"]]["explanation"]), (2, 3))

    def test_part_and_authoring_records_use_exact_canonical_shapes(self):
        part = self.combined_part()
        self.assertEqual(set(part), PART_KEYS)
        self.assertEqual(part["version"], "1.0")
        for module in part["modules"]:
            self.assertEqual(set(module), MODULE_KEYS)
            self.assertTrue(module["id"].startswith("module-"))
        for lesson in part["lessons"]:
            self.assertEqual(set(lesson), LESSON_KEYS)
            self.assertTrue(lesson["id"].startswith("lesson-"))
            self.assertEqual(lesson["contentVersion"], "1.0.0")
            self.assertEqual(lesson["materialSectionIds"], [section["id"] for section in lesson["materialSections"]])
            self.assertEqual(lesson["objectiveIds"], [objective["id"] for objective in lesson["learningObjectives"]])
            for objective in lesson["learningObjectives"]:
                self.assertEqual(set(objective), OBJECTIVE_KEYS)
                self.assertTrue(objective["id"].startswith("objective-"))
                self.assertEqual(objective["moduleId"], lesson["moduleId"])
                self.assertGreaterEqual(len(objective["sourceRefs"]), 1)
            self.assertGreaterEqual(len(lesson["learningObjectives"]), 3)
            origins = set()
            for expected_order, section in enumerate(lesson["materialSections"], 1):
                self.assertEqual(set(section), SECTION_KEYS)
                self.assertTrue(section["id"].startswith("material-section-"))
                self.assertEqual(section["order"], expected_order)
                origins.add(section["origin"])
                expected_label = "Source material" if section["origin"] == "source" else "Generated study guidance"
                self.assertEqual(section["label"], expected_label)
                self.assertEqual(section["generatedStudyGuidance"], section["origin"] == "generated")
                self.assertIn(len(section["explanation"]), range(2, 6))
                self.assertEqual(section["body"], "\n\n".join(section["explanation"]))
                self.assertIn(len(section["recap"]), range(3, 8))
                self.assertGreaterEqual(len(section["sourceRefs"]), 1)
                for item in section["keyTerms"]:
                    self.assertEqual(set(item), {"term", "definition", "sourceRefs"})
                    self.assertTrue(item["sourceRefs"])
                for item in section["workedExamples"]:
                    self.assertEqual(set(item), {"title", "body", "sourceRefs"})
                    self.assertTrue(item["sourceRefs"])
                for item in section["commonMistakes"]:
                    self.assertEqual(set(item), {"misconception", "correction", "sourceRefs"})
                    self.assertTrue(item["sourceRefs"])
                for item in section["examTips"]:
                    self.assertEqual(set(item), {"body", "sourceRefs"})
                    self.assertTrue(item["sourceRefs"])
            self.assertEqual(origins, {"source", "generated"})
            for field in ("keyTerms", "workedExamples", "commonMistakes", "examTips"):
                self.assertTrue(any(section[field] for section in lesson["materialSections"]), f"{lesson['id']} lacks {field}")

    def test_source_references_resolve_within_teaching_page_bounds(self):
        part = self.combined_part()
        sources = {source["id"]: source for source in self.manifest["sources"]}
        classifications = {
            (page["sourceId"], page["page"]): page["classification"]
            for page in self.extraction["pages"]
        }
        all_refs = list(self.iter_source_refs(part))
        self.assertTrue(all_refs)
        for source_ref in all_refs:
            self.assertEqual(set(source_ref), {"sourceId", "locationType", "location"})
            self.assertIn(source_ref["sourceId"], sources)
            self.assertEqual(source_ref["locationType"], "page")
            self.assertIn(source_ref["location"], range(1, sources[source_ref["sourceId"]]["pages"] + 1))
            self.assertEqual(classifications[(source_ref["sourceId"], source_ref["location"])], "teaching")

    def test_module_objectives_and_lesson_question_links_resolve_in_order(self):
        part = self.combined_part()
        question_ids = {question["id"] for question in part["questions"]}
        for module in part["modules"]:
            module_lessons = [lesson for lesson in part["lessons"] if lesson["moduleId"] == module["id"]]
            expected_objectives = [objective["id"] for lesson in module_lessons for objective in lesson["learningObjectives"]]
            self.assertEqual(module["objectiveIds"], expected_objectives)
            orders = [objective["order"] for lesson in module_lessons for objective in lesson["learningObjectives"]]
            self.assertEqual(orders, list(range(1, len(orders) + 1)))
        for lesson in part["lessons"]:
            owned_question_ids = {question["id"] for question in self.questions_for_lesson(part, lesson["id"])}
            self.assertEqual(len(owned_question_ids), 10)
            for section in lesson["materialSections"]:
                self.assertEqual(len(section["linkedQuestionIds"]), len(set(section["linkedQuestionIds"])))
                self.assertTrue(set(section["linkedQuestionIds"]).issubset(owned_question_ids))
                self.assertTrue(set(section["linkedQuestionIds"]).issubset(question_ids))
            self.assertEqual(
                {question_id for section in lesson["materialSections"] for question_id in section["linkedQuestionIds"]},
                owned_question_ids,
            )

    def test_question_counts_quotas_and_deterministic_true_false_patterns(self):
        part = self.combined_part()
        self.assertEqual(Counter(question["type"] for question in part["questions"]), {"mcq": 126, "true-false": 84})
        patterns = ["TTFF", "TFTF", "TFFT", "FTTF", "FTFT", "FFTT"]
        true_false_answers = []
        for lesson in part["lessons"]:
            questions = self.questions_for_lesson(part, lesson["id"])
            expected_ids = [lesson["id"].replace("lesson-", "gq-") + f"-{number:03d}" for number in range(1, 11)]
            self.assertEqual([question["id"] for question in questions], expected_ids)
            self.assertEqual(Counter(question["type"] for question in questions), {"mcq": 6, "true-false": 4})
            self.assertEqual(Counter(question["difficulty"] for question in questions), {"easy": 3, "medium": 5, "hard": 2})
            self.assertEqual(Counter(question["bloomLevel"] for question in questions), {"remember": 3, "apply": 5, "analyze": 2})
            self.assertTrue(all(question["bloomLevel"] == question["cognitiveLevel"] for question in questions))
            true_false = sorted((question for question in questions if question["type"] == "true-false"), key=lambda item: item["id"])
            digest = hashlib.sha256(f"operating-systems-study\n{lesson['id']}".encode("utf-8")).hexdigest()
            expected_pattern = patterns[int(digest[:8], 16) % len(patterns)]
            actual_pattern = "".join("T" if question["correctAnswer"] else "F" for question in true_false)
            self.assertEqual(actual_pattern, expected_pattern)
            true_false_answers.extend(question["correctAnswer"] for question in true_false)
        self.assertEqual(Counter(true_false_answers), {True: 42, False: 42})

    def test_generated_questions_use_exact_answer_evidence_and_provenance_shapes(self):
        part = self.combined_part()
        lesson_objectives = {
            lesson["id"]: set(lesson["objectiveIds"])
            for lesson in part["lessons"]
        }
        for question in part["questions"]:
            lesson_id = "lesson-" + question["id"].removeprefix("gq-").rsplit("-", 1)[0]
            self.assertIn(question["learningObjectiveId"], lesson_objectives[lesson_id])
            self.assertEqual(question["origin"], "generated")
            self.assertEqual(question["generationMethod"], "source-grounded-authoring-v1")
            self.assertEqual(question["contentVersion"], "1.0.0")
            self.assertEqual(set(question["provenance"]), {"sourceRefs", "modelVersion", "promptVersion"})
            self.assertEqual(question["provenance"]["sourceRefs"], question["sourceRefs"])
            self.assertTrue(question["provenance"]["modelVersion"])
            self.assertEqual(question["provenance"]["promptVersion"], "os-question-generation-1.0")
            self.assertEqual(set(question["duplicateComparison"]), {"algorithmVersion", "normalizedPrompt", "candidateIds", "matchClass"})
            self.assertEqual(question["duplicateComparison"]["normalizedPrompt"], self.normalized_prompt(question["prompt"]))
            self.assertEqual(question["duplicateComparison"]["candidateIds"], [])
            self.assertEqual(question["duplicateComparison"]["matchClass"], "none")
            if question["type"] == "mcq":
                self.assertEqual(set(question), QUESTION_COMMON_KEYS | {"options", "distractorRationales"})
                self.assertEqual(len(question["options"]), 4)
                self.assertEqual(len(set(question["options"])), 4)
                self.assertEqual(len(question["distractorRationales"]), 4)
                self.assertIs(type(question["correctAnswer"]), int)
                self.assertIn(question["correctAnswer"], range(4))
                expected_targets = {"prompt", "correctAnswer", "rationale"}
                expected_targets |= {f"options[{index}]" for index in range(4)}
                expected_targets |= {f"distractorRationales[{index}]" for index in range(4)}
            else:
                self.assertEqual(set(question), QUESTION_COMMON_KEYS | {"correctedStatement"})
                self.assertIs(type(question["correctAnswer"]), bool)
                self.assertNotIn("options", question)
                self.assertNotIn("distractorRationales", question)
                if question["correctAnswer"]:
                    self.assertIsNone(question["correctedStatement"])
                else:
                    self.assertIsInstance(question["correctedStatement"], str)
                    self.assertTrue(question["correctedStatement"].strip())
                expected_targets = {"prompt", "correctAnswer", "rationale"}
                if question["correctedStatement"] is not None:
                    expected_targets.add("correctedStatement")
            self.assertEqual([item["target"] for item in question["evidenceMap"]], list(dict.fromkeys(item["target"] for item in question["evidenceMap"])))
            self.assertEqual({item["target"] for item in question["evidenceMap"]}, expected_targets)
            for claim in question["evidenceMap"]:
                self.assertEqual(set(claim), {"claimId", "target", "sourceRefs", "support"})
                self.assertTrue(claim["claimId"])
                self.assertTrue(claim["sourceRefs"])
                self.assertIn(claim["support"], {"direct", "derived"})

    def test_mcq_options_have_precise_source_grounded_evidence(self):
        part = self.combined_part()
        page_text = {
            (page["sourceId"], page["page"]): page["text"]
            for page in self.extraction["pages"]
        }
        uniform_option_evidence = Counter()
        direct_option_claims = Counter()
        option_claims = Counter()
        for question in (item for item in part["questions"] if item["type"] == "mcq"):
            if question["id"].startswith(("gq-os-ch01-", "gq-os-ch02-")):
                part_name = "ch01-ch02"
            elif question["id"].startswith(("gq-os-ch03-", "gq-os-ch05-")):
                part_name = "ch03-ch05"
            else:
                part_name = "ch06-ch08-ch09"
            evidence = {item["target"]: item for item in question["evidenceMap"]}
            signatures = []
            for index, option in enumerate(question["options"]):
                option_claim = evidence[f"options[{index}]"]
                rationale_claim = evidence[f"distractorRationales[{index}]"]
                signatures.append((
                    tuple((ref["sourceId"], ref["location"]) for ref in option_claim["sourceRefs"]),
                    option_claim["support"],
                ))
                source_text = " ".join(
                    page_text[(ref["sourceId"], ref["location"])]
                    for ref in option_claim["sourceRefs"]
                )
                option_tokens = self.content_tokens(option, EVIDENCE_STOP_WORDS)
                source_tokens = self.content_tokens(source_text, EVIDENCE_STOP_WORDS)
                self.assertTrue(
                    option_tokens & source_tokens,
                    f"{question['id']} option {index} has no lexical grounding in its cited pages",
                )
                self.assertLessEqual(len(option_claim["sourceRefs"]), 2)
                self.assertEqual(rationale_claim["sourceRefs"], option_claim["sourceRefs"])
                self.assertEqual(rationale_claim["support"], "derived")
                option_claims[part_name] += 1
                direct_option_claims[part_name] += option_claim["support"] == "direct"
            uniform_option_evidence[part_name] += len(set(signatures)) == 1
        for part_name in ("ch01-ch02", "ch03-ch05", "ch06-ch08-ch09"):
            self.assertLessEqual(uniform_option_evidence[part_name], 8)
            self.assertLess(direct_option_claims[part_name], option_claims[part_name])

    def test_mcq_answer_indexes_match_the_manually_verified_source_oracle(self):
        part = self.combined_part()
        actual = {
            question["id"]: question["correctAnswer"]
            for question in part["questions"]
            if question["type"] == "mcq"
        }
        expected_answers = VERIFIED_MCQ_ANSWER_KEY | PART_THREE_MCQ_ANSWER_KEY
        self.assertEqual(set(actual), set(expected_answers))
        for question_id, expected_answer in expected_answers.items():
            self.assertEqual(
                actual[question_id],
                expected_answer,
                f"{question_id} answer index drifted from the source-verified oracle",
            )

    def test_analyze_items_require_multistep_reasoning_signals(self):
        part = self.combined_part()
        analyze_items = [question for question in part["questions"] if question["bloomLevel"] == "analyze"]
        self.assertEqual(len(analyze_items), 42)
        reasoning_signal = re.compile(
            r"\b(after|although|before|because|compared|despite|diagnos|fails?|observes?|rather than|sequence|trade-off|when|while)\b",
            re.IGNORECASE,
        )
        for question in analyze_items:
            self.assertGreaterEqual(len(question["prompt"].split()), 18, question["id"])
            self.assertRegex(question["prompt"], reasoning_signal, question["id"])
            self.assertGreaterEqual(len(self.proposition_tokens(question)), 10, question["id"])

    def test_validated_questions_do_not_repeat_semantic_propositions(self):
        part = self.combined_part()
        known_pairs = {
            frozenset(("gq-os-ch01-part1-002", "gq-os-ch01-part1-007")),
            frozenset(("gq-os-ch01-part1-004", "gq-os-ch01-part1-009")),
            frozenset(("gq-os-ch01-part3-002", "gq-os-ch01-part3-005")),
            frozenset(("gq-os-ch02-part1-005", "gq-os-ch02-part1-010")),
            frozenset(("gq-os-ch02-part1-006", "gq-os-ch02-part1-009")),
            frozenset(("gq-os-ch02-part2-006", "gq-os-ch02-part2-008")),
            frozenset(("gq-os-ch02-part3-001", "gq-os-ch02-part3-007")),
            frozenset(("gq-os-ch02-part3-005", "gq-os-ch02-part3-009")),
        }
        observed_pairs = set()
        for lesson in part["lessons"]:
            questions = self.questions_for_lesson(part, lesson["id"])
            for left_index, left in enumerate(questions):
                for right in questions[left_index + 1:]:
                    left_tokens = self.proposition_tokens(left)
                    right_tokens = self.proposition_tokens(right)
                    overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
                    pair = frozenset((left["id"], right["id"]))
                    if pair in known_pairs:
                        observed_pairs.add(pair)
                        self.assertLess(overlap, 0.35, f"known semantic overlap remains: {sorted(pair)}")
                    self.assertLess(overlap, 0.42, f"semantic near-duplicate remains: {left['id']} / {right['id']}")
        self.assertEqual(observed_pairs, known_pairs)
        for question in part["questions"]:
            self.assertEqual(question["duplicateComparison"]["candidateIds"], [])
            self.assertEqual(question["duplicateComparison"]["matchClass"], "none")

    def test_prompts_are_unique_and_validated_review_states_are_consistent(self):
        part = self.combined_part()
        normalized = [question["duplicateComparison"]["normalizedPrompt"] for question in part["questions"]]
        self.assertEqual(len(normalized), len(set(normalized)))
        for lesson in part["lessons"]:
            self.assertFalse(lesson["needsReview"])
            self.assertEqual(lesson["reviewNotes"], "")
            self.assertEqual(lesson["review"], {"status": "validated"})
            for section in lesson["materialSections"]:
                self.assertFalse(section["needsReview"])
                self.assertEqual(section["reviewNotes"], "")
        for question in part["questions"]:
            self.assertEqual(question["qualityState"], "validated")
            self.assertEqual(question["reviewState"], "unreviewed")
            self.assertEqual(question["duplicateDisposition"], "retain")
            self.assertFalse(question["needsReview"])
            self.assertEqual(question["reviewNotes"], "")
            self.assertEqual(question["review"], {"status": "validated"})
            self.assertNotIn("approval", question["review"])

    def test_arabic_explanations_use_exact_shape_and_match_questions(self):
        part = self.combined_part()
        questions = {question["id"]: question for question in part["questions"]}
        self.assertEqual(len(part["explanations"]), 210)
        self.assertEqual(len({item["id"] for item in part["explanations"]}), 210)
        for item in part["explanations"]:
            self.assertEqual(set(item), EXPLANATION_KEYS)
            self.assertEqual(item["id"], f"explanation-{item['questionId']}-ar")
            self.assertEqual(questions[item["questionId"]]["generatedExplanationId"], item["id"])
            self.assertEqual(item["language"], "ar")
            self.assertTrue(item["generatedStudyGuidance"])
            self.assertTrue(ARABIC_RE.search(item["translation"]))
            self.assertIn(len(item["explanation"]), (2, 3))
            self.assertTrue(all(ARABIC_RE.search(paragraph) for paragraph in item["explanation"]))
            self.assertTrue(item["body"].strip())
            self.assertIn("مراجعة مولدة", item["note"])
            self.assertIn("الامتحان", item["note"])
            self.assertEqual(item["contentVersion"], "1.0.0")
            self.assertEqual(item["sourceRefs"], questions[item["questionId"]]["sourceRefs"])
            self.assertFalse(item["needsReview"])
            self.assertEqual(item["reviewNotes"], "")
            self.assertEqual(item["review"], {"status": "validated"})

    def test_new_arabic_explanation_bodies_exactly_join_their_paragraphs(self):
        part = self.load_part("content/os/ch03-ch05.json")
        self.assertEqual(len(part["explanations"]), 70)
        for explanation in part["explanations"]:
            self.assertEqual(explanation["body"], "\n\n".join(explanation["explanation"]))

    def test_new_question_objectives_topics_and_section_links_match_the_source_map(self):
        part = self.load_part("content/os/ch03-ch05.json")
        questions = {question["id"]: question for question in part["questions"]}
        self.assertEqual(set(questions), set(EXPECTED_NEW_QUESTION_METADATA))
        linked_sections = {
            question_id: section["id"]
            for lesson in part["lessons"]
            for section in lesson["materialSections"]
            for question_id in section["linkedQuestionIds"]
        }
        self.assertEqual(set(linked_sections), set(questions))
        for question_id, (objective_id, topic, section_id) in EXPECTED_NEW_QUESTION_METADATA.items():
            self.assertEqual(questions[question_id]["learningObjectiveId"], objective_id, question_id)
            self.assertEqual(questions[question_id]["topic"], topic, question_id)
            self.assertEqual(linked_sections[question_id], section_id, question_id)

    def test_new_arabic_explanations_are_question_specific_and_fully_arabic(self):
        part = self.load_part("content/os/ch03-ch05.json")
        questions = {question["id"]: question for question in part["questions"]}
        second_paragraphs = [explanation["explanation"][1] for explanation in part["explanations"]]
        for explanation in part["explanations"]:
            question = questions[explanation["questionId"]]
            self.assertGreaterEqual(len(ARABIC_RE.findall(explanation["translation"])), 12, explanation["id"])
            for paragraph in explanation["explanation"]:
                self.assertGreaterEqual(len(ARABIC_RE.findall(paragraph)), 25, explanation["id"])
                self.assertGreaterEqual(len(ARABIC_WORD_RE.findall(paragraph)), 12, explanation["id"])
            if question["type"] == "true-false" and question["correctedStatement"]:
                self.assertNotIn(question["correctedStatement"], explanation["body"], explanation["id"])
            self.assertNotRegex(explanation["body"], r"التصحيح الكامل للعبارة هو:\s*[A-Z]", explanation["id"])
        self.assertEqual(len(second_paragraphs), len(set(second_paragraphs)))

    def test_new_distractor_rationales_are_distinct_option_specific_rejections(self):
        part = self.load_part("content/os/ch03-ch05.json")
        all_rationales = []
        for question in (item for item in part["questions"] if item["type"] == "mcq"):
            self.assertEqual(len(set(question["distractorRationales"])), 4, question["id"])
            for index, rationale in enumerate(question["distractorRationales"]):
                self.assertFalse(rationale.endswith(question["rationale"]), f"{question['id']} option {index}")
                rationale_tokens = self.content_tokens(rationale, EVIDENCE_STOP_WORDS)
                option_tokens = self.content_tokens(question["options"][index], EVIDENCE_STOP_WORDS)
                self.assertTrue(rationale_tokens & option_tokens, f"{question['id']} option {index}")
                all_rationales.append(self.normalized_prompt(rationale))
        self.assertEqual(len(all_rationales), len(set(all_rationales)))

    def test_exponential_average_true_false_is_valid_at_its_stated_boundaries(self):
        part = self.load_part("content/os/ch03-ch05.json")
        question = next(item for item in part["questions"] if item["id"] == "gq-os-ch05-part2-010")
        self.assertTrue(question["correctAnswer"])
        self.assertIn("0 < alpha < 1", question["prompt"])
        self.assertNotIn("do not exceed one", question["prompt"])
        self.assertEqual(
            {(ref["sourceId"], ref["location"]) for ref in question["sourceRefs"]},
            {("os-lec-12", 7), ("os-lec-12", 10)},
        )

    def test_known_io_wait_duplicate_was_replaced_with_a_distinct_burst_cycle_proposition(self):
        part = self.load_part("content/os/ch03-ch05.json")
        questions = {question["id"]: question for question in part["questions"]}
        replacement = questions["gq-os-ch05-part1-007"]
        self.assertEqual(replacement["topic"], "CPU-I/O burst cycle")
        self.assertIn("final CPU burst", replacement["prompt"])
        left = self.proposition_tokens(questions["gq-os-ch05-part1-003"])
        right = self.proposition_tokens(replacement)
        self.assertLess(len(left & right) / min(len(left), len(right)), 0.25)

    def test_new_mcq_records_match_the_source_verified_immutable_oracle(self):
        part = self.load_part("content/os/ch03-ch05.json")
        mcqs = {question["id"]: question for question in part["questions"] if question["type"] == "mcq"}
        self.assertEqual(set(mcqs), set(NEW_MCQ_SOURCE_VERIFIED_HASHES))
        fields = ("prompt", "options", "correctAnswer", "rationale", "distractorRationales", "evidenceMap")
        for question_id, question in mcqs.items():
            payload = {field: question[field] for field in fields}
            digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
            self.assertEqual(digest, NEW_MCQ_SOURCE_VERIFIED_HASHES[question_id], question_id)

    def test_new_true_false_records_match_the_source_verified_immutable_oracle(self):
        part = self.load_part("content/os/ch03-ch05.json")
        questions = {question["id"]: question for question in part["questions"] if question["type"] == "true-false"}
        self.assertEqual(set(questions), set(NEW_TRUE_FALSE_SOURCE_VERIFIED_HASHES))
        fields = (
            "prompt", "correctAnswer", "rationale", "correctedStatement",
            "learningObjectiveId", "topic", "sourceRefs", "evidenceMap",
        )
        for question_id, question in questions.items():
            payload = {field: question[field] for field in fields}
            digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
            self.assertEqual(digest, NEW_TRUE_FALSE_SOURCE_VERIFIED_HASHES[question_id], question_id)

    def test_new_arabic_explanations_match_the_immutable_oracle(self):
        part = self.load_part("content/os/ch03-ch05.json")
        explanations = {item["questionId"]: item for item in part["explanations"]}
        self.assertEqual(set(explanations), set(NEW_ARABIC_EXPLANATION_HASHES))
        fields = ("translation", "explanation", "body", "note", "sourceRefs")
        for question_id, explanation in explanations.items():
            payload = {field: explanation[field] for field in fields}
            digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
            self.assertEqual(digest, NEW_ARABIC_EXPLANATION_HASHES[question_id], question_id)

    def test_part_three_records_match_independently_transcribed_source_facts(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        mcqs = {question["id"]: question for question in part["questions"] if question["type"] == "mcq"}
        true_false = {question["id"]: question for question in part["questions"] if question["type"] == "true-false"}
        explanations = {item["questionId"]: item for item in part["explanations"]}
        self.assertEqual({question_id: question["correctAnswer"] for question_id, question in mcqs.items()}, PART_THREE_MCQ_ANSWER_KEY)
        self.assertEqual(set(mcqs) | set(true_false), set(PART_THREE_MANUAL_SOURCE_FACTS))
        self.assertEqual(set(explanations), set(PART_THREE_MANUAL_SOURCE_FACTS))
        source_text = {
            (page["sourceId"], page["page"]): re.sub(r"\s+", " ", page["text"].casefold())
            for page in self.extraction["pages"]
        }
        for question_id, (expected_truth, source_id, page, source_phrase) in PART_THREE_MANUAL_SOURCE_FACTS.items():
            question = mcqs.get(question_id) or true_false[question_id]
            self.assertIn(
                (source_id, page),
                {(ref["sourceId"], ref["location"]) for ref in question["sourceRefs"]},
                question_id,
            )
            self.assertIn(source_phrase, source_text[(source_id, page)], question_id)
            if question["type"] == "mcq":
                self.assertIsInstance(expected_truth, int, question_id)
                self.assertNotIsInstance(expected_truth, bool, question_id)
                self.assertEqual(question["correctAnswer"], expected_truth, question_id)
            else:
                self.assertIsInstance(expected_truth, bool, question_id)
                self.assertEqual(question["correctAnswer"], expected_truth, question_id)
                self.assertTrue(question["correctedStatement"] if not expected_truth else True, question_id)

    def test_part_three_manual_oracles_bind_answers_rationales_and_option_evidence(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        mcqs = {question["id"]: question for question in part["questions"] if question["type"] == "mcq"}
        true_false = {question["id"]: question for question in part["questions"] if question["type"] == "true-false"}
        self.assertEqual(set(mcqs), set(PART_THREE_MCQ_OPTION_ORACLES))
        self.assertEqual(set(true_false), set(PART_THREE_TRUE_FALSE_ORACLES))
        source_text = {
            (page["sourceId"], page["page"]): re.sub(r"\s+", " ", page["text"].casefold())
            for page in self.extraction["pages"]
        }

        def evidence_refs(question, target):
            return {
                (ref["sourceId"], ref["location"])
                for claim in question["evidenceMap"] if claim["target"] == target
                for ref in claim["sourceRefs"]
            }

        for question_id, (correct_index, main_anchor, option_records) in PART_THREE_MCQ_OPTION_ORACLES.items():
            question = mcqs[question_id]
            manual_answer, source_id, source_page, source_phrase = PART_THREE_MANUAL_SOURCE_FACTS[question_id]
            self.assertEqual(manual_answer, correct_index, question_id)
            self.assertEqual(question["correctAnswer"], correct_index, question_id)
            self.assertEqual(len(option_records), 4, question_id)
            self.assertEqual(question["options"][correct_index], option_records[correct_index][0], question_id)
            self.assertIn(main_anchor.casefold(), question["rationale"].casefold(), question_id)
            self.assertIn(source_phrase, source_text[(source_id, source_page)], question_id)
            for target in ("prompt", "correctAnswer", "rationale", f"options[{correct_index}]"):
                self.assertIn((source_id, source_page), evidence_refs(question, target), f"{question_id} / {target}")

            categories = []
            for index, (option, category, evidence_page, evidence_phrase, rationale_anchor) in enumerate(option_records):
                self.assertEqual(question["options"][index], option, f"{question_id} option {index}")
                self.assertIn(evidence_phrase.casefold(), source_text[(source_id, evidence_page)], f"{question_id} option {index}")
                self.assertIn((source_id, evidence_page), evidence_refs(question, f"options[{index}]"), f"{question_id} option {index}")
                self.assertIn((source_id, evidence_page), evidence_refs(question, f"distractorRationales[{index}]"), f"{question_id} rationale {index}")
                self.assertIn(rationale_anchor.casefold(), question["distractorRationales"][index].casefold(), f"{question_id} rationale {index}")
                categories.append(category)
            self.assertEqual(len(categories), len(set(categories)), question_id)

        for question_id, (expected_truth, rationale_anchor, correction_anchor) in PART_THREE_TRUE_FALSE_ORACLES.items():
            question = true_false[question_id]
            manual_truth, source_id, source_page, source_phrase = PART_THREE_MANUAL_SOURCE_FACTS[question_id]
            self.assertIsInstance(manual_truth, bool, question_id)
            self.assertEqual(manual_truth, expected_truth, question_id)
            self.assertEqual(question["correctAnswer"], expected_truth, question_id)
            self.assertIn(rationale_anchor.casefold(), question["rationale"].casefold(), question_id)
            self.assertIn(source_phrase, source_text[(source_id, source_page)], question_id)
            for target in ("prompt", "correctAnswer", "rationale"):
                self.assertIn((source_id, source_page), evidence_refs(question, target), f"{question_id} / {target}")
            if expected_truth:
                self.assertIsNone(correction_anchor, question_id)
                self.assertIsNone(question["correctedStatement"], question_id)
            else:
                self.assertIsNotNone(correction_anchor, question_id)
                self.assertIn(correction_anchor.casefold(), question["correctedStatement"].casefold(), question_id)
                self.assertIn((source_id, source_page), evidence_refs(question, "correctedStatement"), question_id)

    def test_part_three_true_false_oracle_rejects_unrelated_statement_and_rationale_mutations(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        question = next(item for item in part["questions"] if item["id"] == "gq-os-ch06-part1-007")
        mutated = {
            **question,
            "prompt": "Interrupts can label an unrelated scheduler record on a single-core system.",
            "rationale": "The unrelated record remains on one core after an interrupt is observed.",
        }
        mutated_support = {
            **question,
            "evidenceMap": [
                {**claim, "support": "derived"} if claim["target"] == "prompt" else claim
                for claim in question["evidenceMap"]
            ],
        }
        self.assertTrue(self.part_three_true_false_matches_oracle(question))
        self.assertFalse(self.part_three_true_false_matches_oracle(mutated))
        self.assertFalse(self.part_three_true_false_matches_oracle(mutated_support))

    def test_part_three_true_false_propositions_and_evidence_supports_are_independent(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        true_false = {question["id"]: question for question in part["questions"] if question["type"] == "true-false"}
        self.assertEqual(set(true_false), set(PART_THREE_TRUE_FALSE_PROPOSITION_ORACLES))
        self.assertEqual(set(true_false), set(PART_THREE_TRUE_FALSE_ORACLES))
        for question_id, question in true_false.items():
            self.assertTrue(self.part_three_true_false_matches_oracle(question), question_id)

    def test_part_three_reviewed_page_corrections_reject_prior_pages(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        questions = {question["id"]: question for question in part["questions"]}
        explanations = {item["questionId"]: item for item in part["explanations"]}
        sections = {
            section["id"]: section
            for lesson in part["lessons"]
            for section in lesson["materialSections"]
        }
        source_text = {
            (page["sourceId"], page["page"]): re.sub(r"\s+", " ", page["text"].casefold())
            for page in self.extraction["pages"]
        }
        for question_id, (source_id, required_page, prior_page, source_phrase, section_id) in PART_THREE_REVIEWED_PAGE_CORRECTIONS.items():
            question = questions[question_id]
            required_ref = (source_id, required_page)
            prior_ref = (source_id, prior_page)
            self.assertIn(source_phrase, source_text[required_ref], question_id)
            self.assertEqual(
                {(ref["sourceId"], ref["location"]) for ref in question["sourceRefs"]},
                {required_ref},
                question_id,
            )
            self.assertNotIn(prior_ref, {(ref["sourceId"], ref["location"]) for ref in question["sourceRefs"]}, question_id)
            expected_supports = {"prompt": "direct", "correctAnswer": "derived", "rationale": "derived"}
            if question["correctedStatement"] is not None:
                expected_supports["correctedStatement"] = "derived"
            for target, support in expected_supports.items():
                claims = [claim for claim in question["evidenceMap"] if claim["target"] == target]
                self.assertEqual(len(claims), 1, f"{question_id} / {target}")
                self.assertEqual(claims[0]["support"], support, f"{question_id} / {target}")
                claim_refs = {(ref["sourceId"], ref["location"]) for ref in claims[0]["sourceRefs"]}
                self.assertEqual(claim_refs, {required_ref}, f"{question_id} / {target}")
                self.assertNotIn(prior_ref, claim_refs, f"{question_id} / {target}")
            self.assertEqual(
                {(ref["sourceId"], ref["location"]) for ref in explanations[question_id]["sourceRefs"]},
                {required_ref},
                question_id,
            )
            self.assertIn(required_ref, {(ref["sourceId"], ref["location"]) for ref in sections[section_id]["sourceRefs"]}, question_id)
            self.assertIn(question_id, sections[section_id]["linkedQuestionIds"], question_id)

    def test_part_three_objective_topic_and_section_mapping_is_semantic(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        questions = {question["id"]: question for question in part["questions"]}
        linked_sections = {
            question_id: section["id"]
            for lesson in part["lessons"]
            for section in lesson["materialSections"]
            for question_id in section["linkedQuestionIds"]
        }
        self.assertEqual(set(questions), set(PART_THREE_QUESTION_METADATA))
        self.assertEqual(set(linked_sections), set(questions))
        for question_id, (objective_id, topic, section_id) in PART_THREE_QUESTION_METADATA.items():
            self.assertEqual(questions[question_id]["learningObjectiveId"], objective_id, question_id)
            self.assertEqual(questions[question_id]["topic"], topic, question_id)
            self.assertEqual(linked_sections[question_id], section_id, question_id)

    def test_part_three_arabic_explanations_are_specific_and_joined_exactly(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        questions = {question["id"]: question for question in part["questions"]}
        explanations = part["explanations"]
        self.assertEqual(len(explanations), 70)
        second_paragraphs = [item["explanation"][1] for item in explanations]
        self.assertEqual(len(second_paragraphs), len(set(second_paragraphs)))
        for item in explanations:
            question = questions[item["questionId"]]
            self.assertGreaterEqual(len(ARABIC_RE.findall(item["translation"])), 12, item["id"])
            self.assertIn(len(item["explanation"]), (2, 3), item["id"])
            self.assertEqual(item["body"], "\n\n".join(item["explanation"]), item["id"])
            for paragraph in item["explanation"]:
                self.assertGreaterEqual(len(ARABIC_RE.findall(paragraph)), 25, item["id"])
                self.assertGreaterEqual(len(ARABIC_WORD_RE.findall(paragraph)), 12, item["id"])
            self.assertEqual(item["sourceRefs"], question["sourceRefs"], item["id"])
            if question["type"] == "true-false" and question["correctedStatement"]:
                self.assertNotIn(question["correctedStatement"], item["body"], item["id"])

    def test_part_three_mcq_distractors_are_distinct_and_option_specific(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        all_rationales = []
        for question in (item for item in part["questions"] if item["type"] == "mcq"):
            self.assertEqual(len(question["distractorRationales"]), 4, question["id"])
            self.assertEqual(len(set(question["distractorRationales"])), 4, question["id"])
            for index, rationale in enumerate(question["distractorRationales"]):
                self.assertFalse(rationale.endswith(question["rationale"]), f"{question['id']} option {index}")
                self.assertTrue(
                    self.content_tokens(rationale, EVIDENCE_STOP_WORDS)
                    & self.content_tokens(question["options"][index], EVIDENCE_STOP_WORDS),
                    f"{question['id']} option {index}",
                )
                all_rationales.append(self.normalized_prompt(rationale))
        self.assertEqual(len(all_rationales), len(set(all_rationales)))

    def test_part_three_source_exercises_lock_their_inputs_and_results(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        questions = {question["id"]: question for question in part["questions"]}

        # Lecture 6.7: execute the independently transcribed instruction trace,
        # then compare it with the two serial executions.
        counter = 5
        producer_register = counter
        producer_register += 1
        consumer_register = counter
        consumer_register -= 1
        counter = producer_register
        counter = consumer_register
        traced_counter = counter
        reverse_write_counter = 5
        reverse_producer_register = reverse_write_counter
        reverse_producer_register += 1
        reverse_consumer_register = reverse_write_counter
        reverse_consumer_register -= 1
        reverse_write_counter = reverse_consumer_register
        reverse_write_counter = reverse_producer_register
        serial_producer_then_consumer = 5 + 1 - 1
        serial_consumer_then_producer = 5 - 1 + 1
        self.assertEqual(
            {traced_counter, reverse_write_counter, serial_producer_then_consumer, serial_consumer_then_producer},
            {4, 5, 6},
        )
        counter_question = questions["gq-os-ch06-part1-009"]
        counter_outcomes = {traced_counter, reverse_write_counter, serial_producer_then_consumer, serial_consumer_then_producer}
        source_number_words = {"four": 4, "five": 5, "six": 6}
        claimed_counter_outcomes = {
            source_number_words[word]
            for word in re.findall(r"\b(?:four|five|six)\b", counter_question["correctedStatement"].casefold())
        }
        statement_is_true = counter_outcomes == {5}
        self.assertEqual(counter_question["correctAnswer"], statement_is_true)
        self.assertEqual(claimed_counter_outcomes, counter_outcomes)

        # Lecture 6.17-6.19: derive Need, perform the safety search, then
        # recompute both request cases instead of checking answer text alone.
        maximum = ((7, 5, 3), (3, 2, 2), (9, 0, 2), (2, 2, 2), (4, 3, 3))
        allocation = ((0, 1, 0), (2, 0, 0), (3, 0, 2), (2, 1, 1), (0, 0, 2))
        available = (3, 3, 2)
        need = tuple(tuple(maximum[index][column] - allocation[index][column] for column in range(3)) for index in range(5))
        self.assertEqual(need, ((7, 4, 3), (1, 2, 2), (6, 0, 0), (0, 1, 1), (4, 3, 1)))

        def safety_sequence(work, allocated, outstanding):
            work = list(work)
            finished = [False] * len(allocated)
            sequence = []
            while True:
                candidate = next(
                    (index for index in range(len(allocated))
                     if not finished[index] and all(outstanding[index][column] <= work[column] for column in range(3))),
                    None,
                )
                if candidate is None:
                    return tuple(sequence), all(finished)
                finished[candidate] = True
                sequence.append(candidate)
                work = [work[column] + allocated[candidate][column] for column in range(3)]

        def listed_sequence_is_safe(work, allocated, outstanding, sequence):
            work = list(work)
            for candidate in sequence:
                if not all(outstanding[candidate][column] <= work[column] for column in range(3)):
                    return False
                work = [work[column] + allocated[candidate][column] for column in range(3)]
            return len(sequence) == len(allocated)

        self.assertTrue(listed_sequence_is_safe(available, allocation, need, (1, 3, 4, 0, 2)))
        initial_sequence, initial_safe = safety_sequence(available, allocation, need)
        self.assertEqual(initial_sequence[0], 1)
        self.assertTrue(initial_safe)
        p1_request = (1, 0, 2)
        self.assertTrue(all(p1_request[column] <= need[1][column] for column in range(3)))
        self.assertTrue(all(p1_request[column] <= available[column] for column in range(3)))
        granted_allocation = list(allocation)
        granted_allocation[1] = tuple(allocation[1][column] + p1_request[column] for column in range(3))
        granted_need = list(need)
        granted_need[1] = tuple(need[1][column] - p1_request[column] for column in range(3))
        granted_available = tuple(available[column] - p1_request[column] for column in range(3))
        self.assertEqual((granted_allocation[1], granted_need[1], granted_available), ((3, 0, 2), (0, 2, 0), (2, 3, 0)))
        self.assertTrue(listed_sequence_is_safe(granted_available, tuple(granted_allocation), tuple(granted_need), (1, 3, 4, 0, 2)))
        self.assertTrue(safety_sequence(granted_available, tuple(granted_allocation), tuple(granted_need))[1])
        p0_request = (0, 2, 0)
        self.assertTrue(all(p0_request[column] <= granted_need[0][column] for column in range(3)))
        self.assertTrue(all(p0_request[column] <= granted_available[column] for column in range(3)))
        p0_allocation = list(granted_allocation)
        p0_allocation[0] = tuple(granted_allocation[0][column] + p0_request[column] for column in range(3))
        p0_need = list(granted_need)
        p0_need[0] = tuple(granted_need[0][column] - p0_request[column] for column in range(3))
        p0_available = tuple(granted_available[column] - p0_request[column] for column in range(3))
        p0_safe = safety_sequence(p0_available, tuple(p0_allocation), tuple(p0_need))[1]
        self.assertFalse(p0_safe)
        self.assertEqual(questions["gq-os-ch08-part2-006"]["correctAnswer"], initial_sequence[0])
        unsafe_question = questions["gq-os-ch08-part2-009"]
        self.assertEqual(unsafe_question["correctAnswer"], p0_safe)
        self.assertIn("unsafe", unsafe_question["correctedStatement"].casefold())
        p1_request_question = questions["gq-os-ch08-part2-010"]
        self.assertEqual(p1_request_question["correctAnswer"], safety_sequence(granted_available, tuple(granted_allocation), tuple(granted_need))[1])
        self.assertIn("(3,0,2)", p1_request_question["prompt"])

        # Lecture 6.17/6.22 and 8.17/8.11: execute the source semaphore
        # transitions and detection state rather than compare canned options.
        synch = 0
        p2_before_p1_can_continue = synch > 0
        synch += 1  # P1 completes S1, then signal(synch).
        p2_after_p1_can_continue = synch > 0
        if p2_after_p1_can_continue:
            synch -= 1
        self.assertEqual((p2_before_p1_can_continue, p2_after_p1_can_continue, synch), (False, True, 0))
        synch_answer = questions["gq-os-ch06-part2-005"]["options"][questions["gq-os-ch06-part2-005"]["correctAnswer"]].casefold()
        self.assertTrue(synch_answer.startswith("zero" if not p2_before_p1_can_continue else "one"))
        self.assertIn("waits", synch_answer)
        self.assertIn("signals", synch_answer)

        producer_trace = ("wait(empty)", "wait(mutex)", "add item", "signal(mutex)", "signal(full)")
        producer_state = {"empty": 2, "mutex": 1, "full": 0, "items": 0}
        for operation in producer_trace:
            if operation.startswith("wait("):
                semaphore = operation[5:-1]
                self.assertGreater(producer_state[semaphore], 0, operation)
                producer_state[semaphore] -= 1
            elif operation.startswith("signal("):
                producer_state[operation[7:-1]] += 1
            else:
                producer_state["items"] += 1
        self.assertEqual(producer_state, {"empty": 1, "mutex": 1, "full": 1, "items": 1})
        producer_answer = questions["gq-os-ch06-part2-006"]["options"][questions["gq-os-ch06-part2-006"]["correctAnswer"]]
        selected_trace = tuple(re.findall(r"wait\([a-z]+\)|signal\([a-z]+\)|add item", producer_answer))
        self.assertEqual(selected_trace, producer_trace)

        held_resource, requested_resource = 5, 4
        request_obeys_order = requested_resource > held_resource
        self.assertFalse(request_obeys_order)
        ordering_answer = questions["gq-os-ch08-part1-006"]["options"][questions["gq-os-ch08-part1-006"]["correctAnswer"]].casefold()
        self.assertEqual("violate" in ordering_answer, not request_obeys_order)
        self.assertIn("increasing", ordering_answer)
        detection_allocation = ((0, 1, 0), (2, 0, 0), (3, 0, 3), (2, 1, 1), (0, 0, 2))
        detection_request = ((0, 0, 0), (2, 0, 2), (0, 0, 1), (1, 0, 0), (0, 0, 2))
        detected_sequence, all_finished = safety_sequence((0, 0, 0), detection_allocation, detection_request)
        self.assertEqual((detected_sequence, all_finished), ((0,), False))
        deadlocked_processes = tuple(f"P{index}" for index in range(len(detection_allocation)) if index not in detected_sequence)
        diagnosis_answer = questions["gq-os-ch08-part3-006"]["options"][questions["gq-os-ch08-part3-006"]["correctAnswer"]]
        self.assertEqual(tuple(re.findall(r"\bP[0-9]\b", diagnosis_answer)), deadlocked_processes)
        self.assertIn("deadlocked", diagnosis_answer.casefold())

        # Lecture 8.13 and 9.5: calculate the two address examples from
        # source inputs and parse the selected result.
        relocation_register, logical_location = 14000, 346
        physical_location = relocation_register + logical_location
        self.assertEqual(physical_location, 14346)
        relocation_answer = questions["gq-os-ch09-part1-006"]["options"][questions["gq-os-ch09-part1-006"]["correctAnswer"]]
        self.assertEqual(int(relocation_answer), physical_location)
        logical_words = 64 * 1024
        address_bits = logical_words.bit_length() - 1
        self.assertEqual(address_bits, 16)
        written_numbers = {"ten": 10, "fifteen": 15, "sixteen": 16, "twenty": 20}
        bit_answer = questions["gq-os-ch09-part2-005"]["options"][questions["gq-os-ch09-part2-005"]["correctAnswer"]].split()[0].casefold()
        self.assertEqual(written_numbers[bit_answer], address_bits)

        # Lecture 9.3-9.14: execute the paging names, translation fields,
        # reentrant mapping, and page-out transition from source statements.
        physical_block_name, logical_block_name = "frames", "pages"
        self.assertNotEqual(physical_block_name, logical_block_name)
        frames_answer = questions["gq-os-ch09-part2-001"]["options"][questions["gq-os-ch09-part2-001"]["correctAnswer"]].casefold()
        self.assertEqual(frames_answer, physical_block_name)

        logical_address = {"page number": 5, "page offset": 346}
        page_table = {5: 9}
        frame_number = page_table[logical_address["page number"]]
        self.assertEqual(frame_number, 9)
        index_answer = questions["gq-os-ch09-part2-002"]["options"][questions["gq-os-ch09-part2-002"]["correctAnswer"]].casefold()
        self.assertEqual(index_answer, next(field for field in logical_address if field == "page number"))

        registers = {"PTBR": page_table, "PTLR": len(page_table)}
        self.assertIs(registers["PTBR"], page_table)
        ptbr_answer = questions["gq-os-ch09-part2-003"]["options"][questions["gq-os-ch09-part2-003"]["correctAnswer"]].casefold()
        self.assertEqual(ptbr_answer, "the page table")
        protection_bit_values = {0: "read-only", 1: "read-write"}
        self.assertEqual({*protection_bit_values.values()}, {"read-only", "read-write"})
        protection_answer = questions["gq-os-ch09-part2-004"]["options"][questions["gq-os-ch09-part2-004"]["correctAnswer"]].casefold()
        self.assertTrue(all(value in protection_answer for value in protection_bit_values.values()))

        library_frame = "frame-17"
        process_mappings = {"P1": library_frame, "P2": library_frame, "P3": library_frame}
        physical_copies = len(set(process_mappings.values()))
        self.assertEqual((physical_copies, len(process_mappings)), (1, 3))
        shared_mapping_answer = questions["gq-os-ch09-part2-006"]["options"][questions["gq-os-ch09-part2-006"]["correctAnswer"]].casefold()
        self.assertTrue(all(term in shared_mapping_answer for term in ("same", "read-only", "all three")))

        memory, backing_store = {"page-7"}, set()
        page_out = memory.pop()
        backing_store.add(page_out)
        page_out_origin, page_out_destination = "memory", "backing store"
        self.assertEqual((memory, backing_store), (set(), {"page-7"}))
        incorrect_page_out_origin, incorrect_page_out_destination = "backing store", "main memory"
        page_out_claim_is_true = (incorrect_page_out_origin, incorrect_page_out_destination) == (page_out_origin, page_out_destination)
        page_out_question = questions["gq-os-ch09-part2-008"]
        self.assertEqual(page_out_question["correctAnswer"], page_out_claim_is_true)
        self.assertIn(f"{page_out_origin} to {page_out_destination}", page_out_question["correctedStatement"].casefold())

        def handle_valid_page_fault(valid_reference, resident, free_frames):
            if not valid_reference:
                return {"terminated": True, "restarted": False, "valid_invalid_bit": "i"}
            if resident:
                return {"terminated": False, "restarted": False, "valid_invalid_bit": "v"}
            frame = free_frames.pop(0)
            return {
                "terminated": False,
                "restarted": True,
                "valid_invalid_bit": "v",
                "frame": frame,
                "events": ("trap", "validate", "find-free-frame", "page-in", "set-v", "restart"),
            }

        fault_result = handle_valid_page_fault(True, False, ["frame-2"])
        self.assertEqual(fault_result["events"], ("trap", "validate", "find-free-frame", "page-in", "set-v", "restart"))
        page_fault_question = questions["gq-os-ch09-part2-010"]
        self.assertEqual(page_fault_question["correctAnswer"], fault_result["restarted"] and not fault_result["terminated"])
        self.assertIn(fault_result["valid_invalid_bit"], page_fault_question["prompt"])

    def test_cross_part_ids_and_semantic_propositions_are_unique(self):
        parts = self.existing_parts()
        combined = self.combined_part()
        id_groups = [
            combined["modules"],
            combined["lessons"],
            [objective for lesson in combined["lessons"] for objective in lesson["learningObjectives"]],
            [section for lesson in combined["lessons"] for section in lesson["materialSections"]],
            combined["questions"],
            combined["explanations"],
        ]
        for records in id_groups:
            ids = [record["id"] for record in records]
            self.assertEqual(len(ids), len(set(ids)))
        semantic_signatures = []
        for question in combined["questions"]:
            answer = (
                question["options"][question["correctAnswer"]]
                if question["type"] == "mcq"
                else question["correctedStatement"] or str(question["correctAnswer"])
            )
            semantic_signatures.append(self.normalized_prompt(" ".join((question["prompt"], question["rationale"], answer))))
        self.assertEqual(len(semantic_signatures), len(set(semantic_signatures)))
        for left_index, left_part in enumerate(parts):
            for right_part in parts[left_index + 1:]:
                for left_question in left_part["questions"]:
                    for right_question in right_part["questions"]:
                        left_tokens = self.proposition_tokens(left_question)
                        right_tokens = self.proposition_tokens(right_question)
                        overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
                        self.assertLess(
                            overlap,
                            0.58,
                            f"cross-part semantic near-duplicate: {left_question['id']} / {right_question['id']}",
                        )

    def test_generated_guidance_is_arabic_and_prohibited_official_claims_are_absent(self):
        part = self.combined_part()
        for lesson in part["lessons"]:
            for section in lesson["materialSections"]:
                if section["origin"] == "generated":
                    self.assertTrue(ARABIC_RE.search(section["summary"]))
                    self.assertTrue(all(ARABIC_RE.search(paragraph) for paragraph in section["explanation"]))
        serialized = json.dumps(part, ensure_ascii=False).casefold()
        for prohibited in (
            "official exam question", "official question", "from the exam",
            "past-paper question", "certified", "guaranteed to appear",
        ):
            self.assertNotIn(prohibited, serialized)

    def test_part_three_binds_each_distractor_to_a_reviewed_misconception(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        mcqs = {item["id"]: item for item in part["questions"] if item["type"] == "mcq"}
        self.assertEqual(set(mcqs), set(PART_THREE_MCQ_OPTION_ORACLES))
        for question_id, question in mcqs.items():
            _, _, option_records = PART_THREE_MCQ_OPTION_ORACLES[question_id]
            self.assertEqual(len(option_records), 4, question_id)
            self.assertEqual(question["options"], [record[0] for record in option_records], question_id)
            categories = [record[1] for record in option_records]
            self.assertEqual(len(categories), len(set(categories)), question_id)
            self.assertTrue(all(category.strip() for category in categories), question_id)

    def test_part_three_arabic_explanations_translate_conditions_and_reject_templates(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        explanations = {item["questionId"]: item for item in part["explanations"]}
        boilerplate = (
            "ما العبارة أو الاختيار الذي يطابق القاعدة المعروضة",
            "يركز هذا السؤال على",
            "اتبع الدليل في الصفحة المحددة",
            "هذا التحليل يفسر الاختيار الصحيح",
            "ويجب ربط النتيجة بكل تفاصيل الشرط المعروض في صياغة هذا السؤال",
            "وتظل المقارنة بين البدائل مرتبطة بالآلية المحددة لا باسمها فقط",
            "فهذا القيد يميز الإجابة الصحيحة عن التفسير القريب لكنه غير المكتمل",
            "وتوضح الحالة لماذا لا يصح تبديل النتيجة أو حذف جزء من المعطيات",
            "ويعتمد الحكم على التسلسل أو العلاقة المذكورة في النص دون افتراض إضافي",
            "ولهذا لا يكفي تذكر المصطلح من دون تطبيقه على الحالة المحددة",
            "وتبقى القيمة أو الحالة المعطاة جزءًا لازمًا من التفسير الصحيح",
            "ويفصل هذا الشرط بين البديل المعقول والاختيار الذي تدعمه المحاضرة",
            "وبذلك تتصل القاعدة مباشرة بالخطوة أو المقارنة الواردة في السؤال",
            "ولا يجوز نقل النتيجة إلى آلية أخرى تختلف في الشرط أو الغرض",
        )
        self.assertEqual(set(explanations), set(PART_THREE_ARABIC_TRANSLATION_ANCHORS))
        all_paragraphs = []
        for question in part["questions"]:
            explanation = explanations[question["id"]]
            combined = " ".join((explanation["translation"], *explanation["explanation"]))
            self.assertFalse(any(phrase in combined for phrase in boilerplate), question["id"])
            self.assertTrue(
                any(anchor in explanation["translation"] for anchor in PART_THREE_ARABIC_TRANSLATION_ANCHORS[question["id"]]),
                question["id"],
            )
            for token in re.findall(r"\d+", question["prompt"]):
                self.assertIn(token, explanation["translation"], question["id"])
            all_paragraphs.extend(self.normalized_prompt(paragraph) for paragraph in explanation["explanation"])
        self.assertEqual(len(all_paragraphs), len(set(all_paragraphs)))

    def test_part_three_question_source_pages_are_contained_by_linked_sections(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        question_sections = {
            question_id: section
            for lesson in part["lessons"]
            for section in lesson["materialSections"]
            for question_id in section["linkedQuestionIds"]
        }
        for question in part["questions"]:
            section = question_sections[question["id"]]
            allowed = {(ref["sourceId"], ref["location"]) for ref in section["sourceRefs"]}
            question_pages = {(ref["sourceId"], ref["location"]) for ref in question["sourceRefs"]}
            self.assertTrue(question_pages <= allowed, question["id"])

    def test_part_three_analyze_items_are_independently_classified_as_reasoning(self):
        part = self.load_part("content/os/ch06-ch08-ch09.json")
        questions = {item["id"]: item for item in part["questions"]}
        expected = {
            "gq-os-ch06-part1-006": ("diagnosis", ("interest", "turn")),
            "gq-os-ch06-part1-009": ("trace", ("five", "increment", "decrement")),
            "gq-os-ch06-part2-006": ("trace", ("producer", "wait", "signal")),
            "gq-os-ch06-part2-009": ("diagnosis", ("higher-priority", "lower-priority", "lock")),
            "gq-os-ch08-part1-006": ("trade-off", ("p1", "r5", "r4")),
            "gq-os-ch08-part1-009": ("comparison", ("unique number", "increasing order", "circular wait")),
            "gq-os-ch08-part2-006": ("vector comparison", ("(3,3,2)", "(1,2,2)", "p1")),
            "gq-os-ch08-part2-009": ("safety analysis", ("p0", "(0,2,0)", "unsafe")),
            "gq-os-ch08-part3-006": ("state trace", ("p2", "c", "p0")),
            "gq-os-ch08-part3-009": ("trade-off", ("deadlock", "every", "one process")),
            "gq-os-ch09-part1-006": ("calculation", ("14000", "346", "physical")),
            "gq-os-ch09-part1-009": ("diagnosis", ("total memory", "noncontiguous", "holes")),
            "gq-os-ch09-part2-006": ("mapping comparison", ("three", "read-only", "reentrant")),
            "gq-os-ch09-part2-010": ("state trace", ("valid", "free frame", "restarts")),
        }
        self.assertEqual(
            {item["id"] for item in part["questions"] if item["bloomLevel"] == "analyze"},
            set(expected),
        )
        for question_id, (reasoning_type, inputs) in expected.items():
            self.assertIn(reasoning_type, questions[question_id]["topic"].casefold(), question_id)
            self.assertEqual(questions[question_id]["cognitiveLevel"], "analyze", question_id)
            rendered_question = " ".join(
                [questions[question_id]["prompt"], *questions[question_id].get("options", [])]
            ).casefold()
            self.assertTrue(all(value in rendered_question for value in inputs), question_id)


if __name__ == "__main__":
    unittest.main()
