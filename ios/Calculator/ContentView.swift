import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = CalculatorViewModel()

    private let buttonSpacing: CGFloat = 1

    var body: some View {
        GeometryReader { geometry in
            VStack(spacing: 0) {
                displaySection
                    .frame(height: geometry.size.height * 0.28)

                keypadSection(buttonSize: buttonSize(for: geometry))
            }
            .background(Color(red: 0.06, green: 0.06, blue: 0.07))
        }
        .ignoresSafeArea(.container, edges: .bottom)
    }

    private var displaySection: some View {
        VStack(alignment: .trailing, spacing: 8) {
            Spacer()

            if !viewModel.expressionText.isEmpty {
                Text(viewModel.expressionText)
                    .font(.system(size: 18, weight: .regular))
                    .foregroundStyle(Color(red: 0.53, green: 0.53, blue: 0.63))
                    .lineLimit(2)
                    .minimumScaleFactor(0.5)
            }

            Text(viewModel.displayValue)
                .font(.system(size: 64, weight: .light))
                .foregroundStyle(Color(red: 0.94, green: 0.94, blue: 0.96))
                .lineLimit(1)
                .minimumScaleFactor(0.3)
        }
        .frame(maxWidth: .infinity, alignment: .trailing)
        .padding(.horizontal, 24)
        .padding(.bottom, 16)
        .background(Color(red: 0.07, green: 0.07, blue: 0.1))
    }

    private func keypadSection(buttonSize: CGFloat) -> some View {
        VStack(spacing: buttonSpacing) {
            row([
                ("AC", .function, { viewModel.clear() }),
                ("±", .function, { viewModel.toggleSign() }),
                ("%", .function, { viewModel.percentage() }),
                ("÷", .operation, { viewModel.inputOperation(.divide) }),
            ], size: buttonSize)

            row([
                ("7", .number, { viewModel.inputDigit("7") }),
                ("8", .number, { viewModel.inputDigit("8") }),
                ("9", .number, { viewModel.inputDigit("9") }),
                ("×", .operation, { viewModel.inputOperation(.multiply) }),
            ], size: buttonSize)

            row([
                ("4", .number, { viewModel.inputDigit("4") }),
                ("5", .number, { viewModel.inputDigit("5") }),
                ("6", .number, { viewModel.inputDigit("6") }),
                ("−", .operation, { viewModel.inputOperation(.subtract) }),
            ], size: buttonSize)

            row([
                ("1", .number, { viewModel.inputDigit("1") }),
                ("2", .number, { viewModel.inputDigit("2") }),
                ("3", .number, { viewModel.inputDigit("3") }),
                ("+", .operation, { viewModel.inputOperation(.add) }),
            ], size: buttonSize)

            HStack(spacing: buttonSpacing) {
                CalculatorButton(title: "0", type: .number) { viewModel.inputDigit("0") }
                    .frame(width: buttonSize * 2 + buttonSpacing, height: buttonSize)

                CalculatorButton(title: ".", type: .number) { viewModel.inputDigit(".") }
                    .frame(width: buttonSize, height: buttonSize)

                CalculatorButton(title: "=", type: .equals) { viewModel.calculate() }
                    .frame(width: buttonSize, height: buttonSize)
            }
        }
        .background(Color.white.opacity(0.04))
    }

    private func row(
        _ buttons: [(String, ButtonType, () -> Void)],
        size: CGFloat
    ) -> some View {
        HStack(spacing: buttonSpacing) {
            ForEach(0..<buttons.count, id: \.self) { index in
                let (title, type, action) = buttons[index]
                CalculatorButton(title: title, type: type, action: action)
                    .frame(width: size, height: size)
            }
        }
    }

    private func buttonSize(for geometry: GeometryProxy) -> CGFloat {
        let width = (geometry.size.width - 3 * buttonSpacing) / 4
        let keypadHeight = geometry.size.height * 0.72
        let height = (keypadHeight - 4 * buttonSpacing) / 5
        return min(width, height)
    }
}

#Preview {
    ContentView()
}
