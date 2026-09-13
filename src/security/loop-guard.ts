export class ExecutionLoopGuard {
  public static readonly MAX_EXECUTION_DEPTH = 3;

  public static checkExecutionDepth(depth: number = 0): void {
    if (depth > this.MAX_EXECUTION_DEPTH) {
      throw new Error(`ExecutionLoopError: Exceeded maximum execution depth of ${this.MAX_EXECUTION_DEPTH}. Recursive execution cycle blocked.`);
    }
  }
}
