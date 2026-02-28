"""Pipeline DAG (Directed Acyclic Graph) builder."""

from typing import Any

import networkx as nx

from pipelineiq.models import Pipeline, Stage


class PipelineDAG:
    """DAG representation of pipeline stages and their dependencies.
    
    This class builds a directed acyclic graph from a Pipeline IR,
    enabling analysis of:
    - Critical path (longest execution path)
    - Parallelizable groups (stages that can run together)
    - Bottlenecks (stages with many dependents)
    - Stage depth (distance from root)
    """
    
    def __init__(self, pipeline: Pipeline):
        """Build DAG from Pipeline IR.
        
        Args:
            pipeline: Pipeline IR to build DAG from
        """
        self.pipeline = pipeline
        self.graph: nx.DiGraph = nx.DiGraph()
        self._depth_cache: dict[str, int] = {}
        self._build_graph()
    
    def _build_graph(self) -> None:
        """Construct NetworkX DiGraph from pipeline stages."""
        # Add all stages as nodes
        for stage in self.pipeline.stages:
            self.graph.add_node(
                stage.id,
                name=stage.name,
                type=stage.type,
                parallel=stage.parallel,
            )
        
        # Add edges based on dependencies
        for stage in self.pipeline.stages:
            for dep_id in stage.dependencies:
                if dep_id in self.graph:
                    self.graph.add_edge(dep_id, stage.id)
    
    def get_edges(self) -> list[tuple[str, str]]:
        """Get all edges as (from, to) tuples.
        
        Returns:
            List of edge tuples for serialization
        """
        return list(self.graph.edges())
    
    def get_critical_path(self) -> list[str]:
        """Find the critical path (longest path through the DAG).
        
        The critical path represents the minimum execution time,
        assuming all stages take equal time.
        
        Returns:
            List of stage IDs in the critical path
        """
        if not self.graph.nodes():
            return []
        
        # Find all paths and return the longest
        try:
            return nx.dag_longest_path(self.graph)
        except nx.NetworkXError:
            return []
    
    def get_independent_stages(self) -> list[str]:
        """Get stages with no dependencies (root nodes).
        
        These stages can start immediately.
        
        Returns:
            List of stage IDs with no incoming edges
        """
        return [node for node in self.graph.nodes() if self.graph.in_degree(node) == 0]
    
    def get_parallelizable_groups(self) -> list[list[str]]:
        """Get groups of stages that can run in parallel.
        
        Uses topological generations to find stages at the same "level"
        that could potentially run together.
        
        Returns:
            List of lists, where each inner list contains stage IDs
            that can run in parallel
        """
        if not self.graph.nodes():
            return []
        
        try:
            return [list(gen) for gen in nx.topological_generations(self.graph)]
        except nx.NetworkXError:
            return []
    
    def get_bottlenecks(self, threshold: int = 2) -> list[str]:
        """Find bottleneck stages (many stages depend on them).
        
        Args:
            threshold: Minimum number of dependents to be a bottleneck
            
        Returns:
            List of stage IDs that are bottlenecks
        """
        bottlenecks = []
        for node in self.graph.nodes():
            if self.graph.out_degree(node) >= threshold:
                bottlenecks.append(node)
        return bottlenecks
    
    def get_stage_depth(self, stage_id: str) -> int:
        """Get depth of a stage from root.
        
        Depth is the longest path from any root to this stage.
        Uses cached topological depths for O(1) lookup after first call.
        
        Args:
            stage_id: Stage ID to get depth for
            
        Returns:
            Depth (0 for root nodes), -1 if stage not found
        """
        if stage_id not in self.graph:
            return -1
        
        # Build cache if empty
        if not self._depth_cache:
            self._compute_depths()
        
        return self._depth_cache.get(stage_id, -1)
    
    def _compute_depths(self) -> None:
        """Compute depths for all nodes using BFS from roots. O(V+E) complexity."""
        if not self.graph.nodes():
            return
        
        # Initialize depths
        for node in self.graph.nodes():
            self._depth_cache[node] = 0
        
        # Use topological sort to compute max depth from any root
        try:
            for node in nx.topological_sort(self.graph):
                predecessors = list(self.graph.predecessors(node))
                if predecessors:
                    self._depth_cache[node] = max(
                        self._depth_cache[pred] + 1 for pred in predecessors
                    )
        except nx.NetworkXError:
            pass  # Graph has cycles or is empty
    
    def get_dependents(self, stage_id: str) -> list[str]:
        """Get stages that depend on the given stage.
        
        Args:
            stage_id: Stage to find dependents for
            
        Returns:
            List of stage IDs that depend on the given stage
        """
        if stage_id not in self.graph:
            return []
        return list(self.graph.successors(stage_id))
    
    def get_dependencies(self, stage_id: str) -> list[str]:
        """Get stages that the given stage depends on.
        
        Args:
            stage_id: Stage to find dependencies for
            
        Returns:
            List of stage IDs that the given stage depends on
        """
        if stage_id not in self.graph:
            return []
        return list(self.graph.predecessors(stage_id))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert DAG to dictionary representation.
        
        Returns:
            Dictionary with nodes and edges
        """
        return {
            "nodes": [
                {
                    "id": node,
                    **self.graph.nodes[node],
                }
                for node in self.graph.nodes()
            ],
            "edges": [
                {"from": u, "to": v}
                for u, v in self.graph.edges()
            ],
        }
