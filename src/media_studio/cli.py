import argparse
import json
from pathlib import Path
from .agent_tools import plan_render, render_local
from .providers import ComfyUI


def main() -> None:
    parser = argparse.ArgumentParser(description="Local H3 showcase tools")
    parser.add_argument("command", choices=["plan", "preflight", "render"])
    parser.add_argument("--workflow", default="examples/environment/workflow.json")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8188")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--prompt")
    parser.add_argument("--out", default="runs/environment")
    parser.add_argument("--timeout", type=float, default=2700)
    args = parser.parse_args()
    if args.command == "plan":
        result = plan_render(args.workflow, args.seed, args.prompt)
    elif args.command == "preflight":
        result = ComfyUI(args.endpoint).preflight(plan_render(args.workflow, args.seed, args.prompt))
    else:
        result = render_local(args.workflow, args.out, args.endpoint, args.seed, args.prompt, args.timeout)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
