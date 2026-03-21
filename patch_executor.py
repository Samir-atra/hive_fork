with open("core/framework/graph/executor.py", "r") as f:
    text = f.read()

target = """                total_tokens += result.tokens_used
                total_latency += result.latency_ms

                # Handle failure"""

replacement = """                total_tokens += result.tokens_used
                total_latency += result.latency_ms

                # Enforce budget and fast-fail
                try:
                    budget.record(result.tokens_used, node_id=current_node_id)
                except TokenBudgetExceededError as e:
                    self.logger.error(f"🛑 {str(e)}")
                    return ExecutionResult(
                        success=False,
                        error=str(e),
                        output=result.output,
                        total_tokens=total_tokens,
                        total_latency=total_latency,
                        steps_executed=steps_executed,
                        path=path,
                    )

                # Handle failure"""

text = text.replace(target, replacement)

target2 = """                        total_tokens += branch_tokens
                        total_latency += branch_latency

                        # Continue from fan-in node"""

replacement2 = """                        total_tokens += branch_tokens
                        total_latency += branch_latency

                        # Enforce budget for parallel branches
                        try:
                            budget.record(branch_tokens, node_id="<parallel_branches>")
                        except TokenBudgetExceededError as e:
                            self.logger.error(f"🛑 {str(e)}")
                            return ExecutionResult(
                                success=False,
                                error=str(e),
                                output=result.output,
                                total_tokens=total_tokens,
                                total_latency=total_latency,
                                steps_executed=steps_executed,
                                path=path,
                            )

                        # Continue from fan-in node"""

text = text.replace(target2, replacement2)

with open("core/framework/graph/executor.py", "w") as f:
    f.write(text)
