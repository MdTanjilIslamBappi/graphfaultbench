from gemma_research.data.types import CodeGraph, Edge, Node
from gemma_research.evidence.gemma_rerank import gemma_rerank


def _repo_graph() -> CodeGraph:
    nodes = (
        Node("auth.login", "toy", "function", "login function handles user authentication"),
        Node("auth.logout", "toy", "function", "logout function clears session"),
        Node("db.query", "toy", "function", "query function executes database query"),
        Node("db.connect", "toy", "function", "connect function opens database connection"),
        Node("util.hash", "toy", "function", "hash function computes password hash"),
    )
    edges = (
        Edge("auth.login", "db.query", "calls"),
        Edge("auth.login", "util.hash", "calls"),
        Edge("db.query", "db.connect", "calls"),
    )
    return CodeGraph(repo="toy", commit="abc", nodes=nodes, edges=edges)


class _FakeLlm:
    """Stands in for llama_cpp.Llama so parsing logic can be tested without
    loading the real ~3.3 GB checkpoint."""

    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.last_messages = None

    def create_chat_completion(self, messages, max_tokens, temperature, top_p, top_k):
        self.last_messages = messages
        return {
            "choices": [{"message": {"content": self.response_text}}],
            "usage": {"prompt_tokens": 42, "completion_tokens": 7},
        }


def test_gemma_rerank_parses_clean_node_id_lines():
    graph = _repo_graph()
    llm = _FakeLlm("auth.login\ndb.query\nutil.hash")
    result = gemma_rerank(llm, graph, "authentication login is broken", pool_size=5)
    assert result.n_parsed_valid == 3
    top_ids = [c.node_id for c in result.ranking[:3]]
    assert top_ids == ["auth.login", "db.query", "util.hash"]


def test_gemma_rerank_ignores_hallucinated_ids_not_in_pool():
    graph = _repo_graph()
    llm = _FakeLlm("auth.login\nsome.made.up.symbol\ndb.query")
    result = gemma_rerank(llm, graph, "authentication login is broken", pool_size=5)
    assert result.n_parsed_valid == 2
    assert "some.made.up.symbol" not in {c.node_id for c in result.ranking}


def test_gemma_rerank_falls_back_to_mid_line_token_matching():
    graph = _repo_graph()
    llm = _FakeLlm("1. auth.login - most likely\n2. db.query - also relevant")
    result = gemma_rerank(llm, graph, "authentication login is broken", pool_size=5)
    assert result.n_parsed_valid == 2
    assert result.ranking[0].node_id == "auth.login"


def test_gemma_rerank_handles_empty_or_garbage_output():
    graph = _repo_graph()
    llm = _FakeLlm("I cannot help with that request.")
    result = gemma_rerank(llm, graph, "authentication login is broken", pool_size=5)
    assert result.n_parsed_valid == 0
    # Still returns a full ranking covering the candidate pool (score 0.0 for
    # everything), so downstream Hit@k scoring never crashes on empty output.
    assert len(result.ranking) == 5


def test_gemma_rerank_candidate_pool_respects_pool_size():
    graph = _repo_graph()
    llm = _FakeLlm("auth.login")
    result = gemma_rerank(llm, graph, "authentication login is broken", pool_size=2)
    assert len(result.candidate_pool) == 2
