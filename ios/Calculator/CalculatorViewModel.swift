import Foundation

enum CalculatorOperation: String {
    case add = "+"
    case subtract = "−"
    case multiply = "×"
    case divide = "÷"

    func calculate(_ lhs: Double, _ rhs: Double) -> Double? {
        switch self {
        case .add: return lhs + rhs
        case .subtract: return lhs - rhs
        case .multiply: return lhs * rhs
        case .divide:
            guard rhs != 0 else { return nil }
            return lhs / rhs
        }
    }
}

@MainActor
final class CalculatorViewModel: ObservableObject {
    @Published var displayValue = "0"
    @Published var expressionText = ""

    private var currentValue: String = "0"
    private var previousValue: String = ""
    private var operation: CalculatorOperation?
    private var shouldResetDisplay = false

    func inputDigit(_ digit: String) {
        if shouldResetDisplay {
            currentValue = digit == "." ? "0." : digit
            shouldResetDisplay = false
        } else if digit == "." && currentValue.contains(".") {
            return
        } else if currentValue == "0" && digit != "." {
            currentValue = digit
        } else {
            currentValue += digit
        }
        updateDisplay()
    }

    func inputOperation(_ op: CalculatorOperation) {
        if let operation, !shouldResetDisplay {
            calculate()
        }

        previousValue = currentValue
        self.operation = op
        shouldResetDisplay = true
        updateExpression()
    }

    func calculate() {
        guard let operation,
              let prev = Double(previousValue),
              let current = Double(currentValue) else { return }

        guard let result = operation.calculate(prev, current) else {
            showError()
            return
        }

        let resultString = formatResult(result)
        expressionText = "\(formatForDisplay(previousValue)) \(operation.rawValue) \(formatForDisplay(currentValue)) ="
        currentValue = resultString
        previousValue = ""
        self.operation = nil
        shouldResetDisplay = true
        displayValue = formatForDisplay(currentValue)
    }

    func clear() {
        currentValue = "0"
        previousValue = ""
        operation = nil
        shouldResetDisplay = false
        expressionText = ""
        displayValue = "0"
    }

    func toggleSign() {
        guard currentValue != "0", currentValue != "Error" else { return }
        if currentValue.hasPrefix("-") {
            currentValue.removeFirst()
        } else {
            currentValue = "-" + currentValue
        }
        updateDisplay()
    }

    func percentage() {
        guard let num = Double(currentValue) else { return }
        currentValue = formatResult(num / 100)
        shouldResetDisplay = true
        updateDisplay()
    }

    private func showError() {
        currentValue = "Error"
        previousValue = ""
        operation = nil
        shouldResetDisplay = true
        expressionText = ""
        displayValue = "Error"
    }

    private func updateDisplay() {
        displayValue = formatForDisplay(currentValue)
        updateExpression()
    }

    private func updateExpression() {
        guard !previousValue.isEmpty, let operation else {
            if expressionText.contains("=") { return }
            expressionText = ""
            return
        }
        expressionText = "\(formatForDisplay(previousValue)) \(operation.rawValue)"
    }

    private func formatResult(_ value: Double) -> String {
        let rounded = (value * 1e10).rounded() / 1e10
        return String(rounded)
    }

    private func formatForDisplay(_ value: String) -> String {
        guard value != "Error", value != "-", !value.isEmpty else {
            return value.isEmpty ? "0" : value
        }

        if value.hasSuffix(".") {
            let intPart = String(value.dropLast())
            if let num = Int(intPart) {
                return NumberFormatter.localizedString(from: NSNumber(value: num), number: .decimal) + "."
            }
            return value
        }

        guard let num = Double(value) else { return value }

        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.locale = Locale(identifier: "id_ID")
        formatter.maximumFractionDigits = 10
        formatter.minimumFractionDigits = 0

        return formatter.string(from: NSNumber(value: num)) ?? value
    }
}
