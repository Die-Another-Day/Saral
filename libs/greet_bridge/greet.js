// Saral bridge example (Node.js). Protocol: JSON on stdin
// {"verb": "...", "args": [...], "named": {...}} -> JSON on stdout {"result": ...}
// This is a real bridge: Saral (Python) calls Node over this JSON protocol.
const fs = require("fs");
let input = "";
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  let req;
  try {
    req = JSON.parse(input);
  } catch (e) {
    process.stdout.write(JSON.stringify({ error: "bad JSON input" }));
    return;
  }
  const name = req.args && req.args[0] !== undefined ? String(req.args[0]) : "friend";
  if (req.verb === "greet") {
    process.stdout.write(JSON.stringify({ result: "Hello from Node, " + name + "!" }));
  } else if (req.verb === "shout") {
    process.stdout.write(JSON.stringify({ result: name.toUpperCase() + "!" }));
  } else {
    process.stdout.write(JSON.stringify({ error: "unknown verb " + req.verb }));
  }
});
