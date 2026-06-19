import statistics

from app.pipeline.models import DockingResult


class ProbePocketEvaluator:
    """
    Choisit la meilleure poche à partir des résultats du probe docking.

    Stratégie par défaut :
    - grouper les résultats par pocket_id
    - ignorer les résultats sans cnn_pose_score
    - calculer la moyenne des cnn_pose_score par poche
    - choisir la poche avec la meilleure moyenne

    Hypothèse :
    - plus le cnn_pose_score est élevé, meilleure est la qualité prédite des poses.
    """

    def select_best_pocket(self, results: list[DockingResult]) -> str:
        if not results:
            raise ValueError("No probe results provided.")

        scores_by_pocket: dict[str, list[float]] = {}

        for result in results:
            if result.cnn_pose_score is None:
                continue

            pocket_id = result.pocket_id.strip()

            scores_by_pocket.setdefault(pocket_id, []).append(
                result.cnn_pose_score
            )

        if not scores_by_pocket:
            raise ValueError("No valid cnn_pose_score values found in probe results.")

        mean_scores_by_pocket = {
            pocket_id: statistics.mean(scores)
            for pocket_id, scores in scores_by_pocket.items()
            if scores
        }

        best_pocket_id = max(
            mean_scores_by_pocket,
            key=mean_scores_by_pocket.get,
        )

        print(f"[INFO] Probe pocket mean scores: {mean_scores_by_pocket}")
        print(f"[INFO] Best pocket selected: {best_pocket_id}")

        return best_pocket_id