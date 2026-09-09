const assert = require("assert")
const Model = require("../Model.js")

assert.strictEqual(Model.formatDistance(1000, {unit: "meters"}), "1.0 m")
assert.strictEqual(Model.formatDistance(180, {unit: "bananas"}), "1.0 bananas")
assert.strictEqual(Model.formatDistance(1200, {
  unit: "custom", custom_unit: {name: "desks", symbol: "desk", metres_per_unit: 1.2}
}), "1.0 desk")
assert.strictEqual(Model.ratioLabel(0.5), "1 : 2.0")
assert.deepStrictEqual(Model.sortedShortcuts({"Ctrl+V": 2, "Ctrl+C": 5})[0],
                       {name: "Ctrl+C", count: 5})
assert.strictEqual(Model.heat(10, 10), 1)
console.log("Model.js tests passed")
