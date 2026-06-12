from sqlalchemy import func, or_
from sqlalchemy.orm import Session, aliased

from backend.research.models import ResearchEdge, ResearchNode


class GraphService:
    def __init__(self, session: Session):
        self.session = session

    def list_nodes(self, node_type: str | None = None, limit: int = 100) -> list[ResearchNode]:
        query = self.session.query(ResearchNode).order_by(ResearchNode.created_at.desc())
        if node_type:
            query = query.filter(ResearchNode.node_type == node_type)
        return query.limit(limit).all()

    def list_edges(self, edge_type: str | None = None, limit: int = 100) -> list[ResearchEdge]:
        query = self.session.query(ResearchEdge).order_by(ResearchEdge.created_at.desc())
        if edge_type:
            query = query.filter(ResearchEdge.edge_type == edge_type)
        return query.limit(limit).all()

    def get_stats(self) -> dict:
        source_node = aliased(ResearchNode)
        target_node = aliased(ResearchNode)
        duplicate_edges = (
            self.session.query(
                ResearchEdge.source_node_id,
                ResearchEdge.target_node_id,
                ResearchEdge.edge_type,
                func.count(ResearchEdge.id).label("edge_count"),
            )
            .group_by(
                ResearchEdge.source_node_id,
                ResearchEdge.target_node_id,
                ResearchEdge.edge_type,
            )
            .having(func.count(ResearchEdge.id) > 1)
            .subquery()
        )
        orphan_edge_count = (
            self.session.query(func.count(ResearchEdge.id))
            .outerjoin(source_node, ResearchEdge.source_node_id == source_node.id)
            .outerjoin(target_node, ResearchEdge.target_node_id == target_node.id)
            .filter(or_(source_node.id.is_(None), target_node.id.is_(None)))
            .scalar()
            or 0
        )
        duplicate_edge_group_count = (
            self.session.query(func.count()).select_from(duplicate_edges).scalar() or 0
        )
        return {
            "node_count": self.session.query(func.count(ResearchNode.id)).scalar() or 0,
            "edge_count": self.session.query(func.count(ResearchEdge.id)).scalar() or 0,
            "node_type_counts": self._count_by(ResearchNode.node_type),
            "edge_type_counts": self._count_by(ResearchEdge.edge_type),
            "orphan_edge_count": orphan_edge_count,
            "duplicate_edge_group_count": duplicate_edge_group_count,
        }

    def _count_by(self, column) -> dict[str, int]:
        rows = (
            self.session.query(column, func.count().label("item_count"))
            .group_by(column)
            .order_by(func.count().desc(), column.asc())
            .all()
        )
        return {str(value): int(count) for value, count in rows}

    def get_or_create_node(
        self,
        *,
        node_type: str,
        label: str,
        canonical_key: str,
        payload: dict | None = None,
    ) -> ResearchNode:
        node = (
            self.session.query(ResearchNode)
            .filter(
                ResearchNode.node_type == node_type,
                ResearchNode.canonical_key == canonical_key,
            )
            .one_or_none()
        )
        if node is not None:
            if payload:
                node.payload_json = {**(node.payload_json or {}), **payload}
            if label:
                node.label = label
            return node

        node = ResearchNode(
            node_type=node_type,
            label=label,
            canonical_key=canonical_key,
            payload_json=payload or {},
        )
        self.session.add(node)
        self.session.flush()
        return node

    def create_edge(
        self,
        *,
        source_node: ResearchNode,
        target_node: ResearchNode,
        edge_type: str,
        evidence_ids: list[str] | None = None,
        weight: float = 1.0,
        payload: dict | None = None,
    ) -> ResearchEdge:
        edge = ResearchEdge(
            source_node_id=source_node.id,
            target_node_id=target_node.id,
            edge_type=edge_type,
            weight=weight,
            evidence_ids_json=evidence_ids or [],
            payload_json=payload or {},
        )
        self.session.add(edge)
        self.session.flush()
        return edge
