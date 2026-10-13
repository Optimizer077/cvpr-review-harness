### Evidence audit (required in careful mode)
Add this field to both `review.json` and `satisfaction.json`. It is a harness addition, not an official venue form.

```json
"evidence_audit": {
  "coverage": {
    "method": {"status": "checked", "note": "Sec. 3, Eqs. 2-4: checked the objective and its assumptions"}
  },
  "claim_checks": [
    {"claim": "The claimed improvement holds beyond the training setting", "location": "Abstract; Sec. 4", "evidence": "Table 2 tests one shifted setting; broader shifts are untested", "verdict": "partial"}
  ]
}
```
Replace examples with actual observations. `coverage` must have exactly the assigned section keys. Each value needs `status` (`checked` or `not_checked`) and a nonempty `note` with the inspected location or reason it was not checked. `claim_checks` must assess the central claims in scope (at least one); each needs `claim`, `location`, `evidence` and `verdict` (`supported`, `partial`, `unsupported`, `not_checked`). Quote short evidence or identify the precise result/proof; never fabricate a location. A not_checked entry must explain the obstacle and cannot serve as proof of invalidity. The validator checks structure, not truth: the orchestrator must still inspect substantive evidence and incomplete coverage.
