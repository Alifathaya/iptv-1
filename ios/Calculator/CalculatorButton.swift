import SwiftUI

enum ButtonType {
    case number
    case operation
    case function
    case equals

    var backgroundColor: Color {
        switch self {
        case .number: return Color(red: 0.1, green: 0.1, blue: 0.13)
        case .operation: return Color(red: 1.0, green: 0.42, blue: 0.42).opacity(0.2)
        case .function: return Color(red: 0.31, green: 0.8, blue: 0.77).opacity(0.15)
        case .equals: return Color(red: 0.42, green: 0.36, blue: 0.91)
        }
    }

    var foregroundColor: Color {
        switch self {
        case .number: return Color(red: 0.94, green: 0.94, blue: 0.96)
        case .operation: return Color(red: 1.0, green: 0.42, blue: 0.42)
        case .function: return Color(red: 0.31, green: 0.8, blue: 0.77)
        case .equals: return .white
        }
    }
}

struct CalculatorButton: View {
    let title: String
    let type: ButtonType
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: type == .function ? 22 : 28, weight: type == .equals ? .medium : .regular))
                .foregroundStyle(type.foregroundColor)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(type.backgroundColor)
                .contentShape(Rectangle())
        }
        .buttonStyle(CalculatorButtonStyle())
    }
}

struct CalculatorButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.92 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}
