"""
Reproduction test for issue #3341: Client parent_tasks/child_tasks resolve wrong 
tasks when a foreach index is a string prefix of another.

This test creates a flow with 12 foreach items to trigger the prefix collision
(e.g., "middle:1" vs "middle:10" and "middle:11").
"""
from metaflow import FlowSpec, step


class ForeachPrefixFlow(FlowSpec):
    """Test flow with 12 item foreach to reproduce prefix collision bug."""
    
    @step
    def start(self):
        """Start step that creates 12 foreach branches."""
        self.items = list(range(12))
        self.next(self.middle, foreach="items")
    
    @step
    def middle(self):
        """Middle step that processes each item."""
        self.item_value = self.input
        self.next(self.tail)
    
    @step
    def tail(self):
        """Tail step before join."""
        self.result = f"processed_{self.item_value}"
        self.next(self.join)
    
    @step
    def join(self, inputs):
        """Join step that combines all results."""
        self.all_results = [inp.result for inp in inputs]
        self.next(self.end)
    
    @step
    def end(self):
        """End step."""
        print(f"Processed {len(self.all_results)} items")


if __name__ == "__main__":
    ForeachPrefixFlow()
