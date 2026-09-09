function number(value) {
  var n = Number(value)
  return isFinite(n) ? n : 0
}

function compact(value, digits) {
  var n = Math.max(0, number(value))
  if (n >= 1000000000) return (n / 1000000000).toFixed(1) + "B"
  if (n >= 1000000) return (n / 1000000).toFixed(1) + "M"
  if (n >= 1000) return (n / 1000).toFixed(n >= 10000 ? 0 : 1) + "K"
  return n.toFixed(digits === undefined ? 0 : digits)
}

function unitInfo(settings) {
  var mode = settings && settings.unit ? String(settings.unit) : "meters"
  if (mode === "miles") return { metres: 1609.344, symbol: "mi", name: "miles" }
  if (mode === "bananas") return { metres: 0.18, symbol: "bananas", name: "banana lengths" }
  if (mode === "custom") {
    var c = settings && settings.custom_unit ? settings.custom_unit : {}
    var conversion = Math.max(0.000001, number(c.metres_per_unit) || 1)
    return { metres: conversion, symbol: String(c.symbol || "u"), name: String(c.name || "custom units") }
  }
  return { metres: 1, symbol: "m", name: "meters" }
}

function precision(value) {
  var n = Math.abs(number(value))
  if (n === 0) return 0
  if (n < 0.01) return 4
  if (n < 1) return 2
  if (n < 100) return 1
  return 0
}

function formatDistance(mm, settings) {
  var unit = unitInfo(settings)
  var converted = number(mm) / 1000 / unit.metres
  return converted.toFixed(precision(converted)) + " " + unit.symbol
}

function formatSpeed(mmPerSecond, settings) {
  return formatDistance(mmPerSecond, settings) + "/s"
}

function formatDuration(seconds) {
  var total = Math.max(0, Math.floor(number(seconds)))
  var days = Math.floor(total / 86400)
  var hours = Math.floor((total % 86400) / 3600)
  var mins = Math.floor((total % 3600) / 60)
  if (days > 0) return days + "d " + hours + "h"
  if (hours > 0) return hours + "h " + mins + "m"
  if (mins > 0) return mins + "m " + (total % 60) + "s"
  return total + "s"
}

function formatCalories(value) {
  var n = Math.max(0, number(value))
  if (n < 0.01) return n.toFixed(4) + " kcal"
  if (n < 1) return n.toFixed(3) + " kcal"
  return n.toFixed(2) + " kcal"
}

function ratioLabel(value) {
  var ratio = Math.max(0, number(value))
  if (ratio === 0) return "0 : 1"
  if (ratio >= 1) return ratio.toFixed(ratio >= 10 ? 0 : 1) + " : 1"
  return "1 : " + (1 / ratio).toFixed(1)
}

function sortedShortcuts(shortcuts) {
  var result = []
  var source = shortcuts || {}
  for (var key in source) result.push({ name: key, count: number(source[key]) })
  result.sort(function(a, b) { return b.count - a.count || a.name.localeCompare(b.name) })
  return result
}

function maxKeyCount(perKey) {
  var source = perKey || {}
  var maximum = 0
  for (var key in source) maximum = Math.max(maximum, number(source[key]))
  return maximum
}

function heat(count, maximum) {
  var c = Math.max(0, number(count))
  var m = Math.max(0, number(maximum))
  if (c <= 0 || m <= 0) return 0
  return Math.log(1 + c) / Math.log(1 + m)
}

function metricEnabled(settings, key) {
  return !(settings && settings.metrics && settings.metrics[key] === false)
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    compact: compact, unitInfo: unitInfo, formatDistance: formatDistance,
    formatSpeed: formatSpeed, formatDuration: formatDuration,
    formatCalories: formatCalories, ratioLabel: ratioLabel,
    sortedShortcuts: sortedShortcuts, maxKeyCount: maxKeyCount,
    heat: heat, metricEnabled: metricEnabled
  }
}
