import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def build_graph(vectors, threshold: float = 0.5):
    """
    输入：vectors = [{"id": str, "vector": List[float]}, ...]
    输出：{"nodes": [...], "edges": [...]}
    """
    ids = [v["id"] for v in vectors]
    vecs = np.array([v["vector"] for v in vectors])
    sim_matrix = cosine_similarity(vecs)
    nodes = [{"id": id_, "label": id_} for id_ in ids]
    edges = []
    n = len(ids)
    for i in range(n):
        for j in range(i+1, n):
            score = float(sim_matrix[i, j])
            if score >= threshold:
                edges.append({"from": ids[i], "to": ids[j], "weight": score})
    return {"nodes": nodes, "edges": edges}