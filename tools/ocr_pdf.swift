// macOSの標準Vision/PDFKitで、画像PDFを文字にする（追加インストール不要）。
// swift tools/ocr_pdf.swift /private/document.pdf [最初のページ0始まり] [最後のページ]
import Foundation
import AppKit
import PDFKit
import Vision

guard CommandLine.arguments.count >= 2,
      let document = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])) else {
    fputs("PDFを開けません\n", stderr)
    exit(1)
}
let first = CommandLine.arguments.count > 2 ? Int(CommandLine.arguments[2]) ?? 0 : 0
let last = CommandLine.arguments.count > 3 ? Int(CommandLine.arguments[3]) ?? document.pageCount - 1 : document.pageCount - 1
guard document.pageCount > 0, max(0, first) <= min(last, document.pageCount - 1) else {
    fputs("ページ範囲が不正です\n", stderr)
    exit(2)
}
var rows: [[String: Any]] = []
for index in max(0, first)...min(last, document.pageCount - 1) {
    guard let page = document.page(at: index) else { continue }
    let bounds = page.bounds(for: .mediaBox)
    let image = page.thumbnail(of: NSSize(width: bounds.width * 3, height: bounds.height * 3), for: .mediaBox)
    var imageRect = CGRect(origin: .zero, size: image.size)
    guard let cg = image.cgImage(forProposedRect: &imageRect, context: nil, hints: nil) else { continue }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["ja-JP", "en-US"]
    request.usesLanguageCorrection = false
    try VNImageRequestHandler(cgImage: cg).perform([request])
    let text = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
    rows.append(["page": index, "text": text])
}
let data = try JSONSerialization.data(withJSONObject: rows, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes])
FileHandle.standardOutput.write(data)
