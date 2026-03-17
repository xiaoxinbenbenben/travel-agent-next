async function buildCanvas(element: HTMLElement): Promise<HTMLCanvasElement> {
  if (window.__TRAVEL_AGENT_E2E__) {
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(element.offsetWidth, 1200)
    canvas.height = Math.max(element.offsetHeight, 800)
    const context = canvas.getContext('2d')

    if (!context) {
      throw new Error('无法创建导出画布')
    }

    context.fillStyle = '#f7f1e3'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.fillStyle = '#234b3f'
    context.font = 'bold 42px Avenir Next'
    context.fillText('Travel Agent Export Preview', 48, 88)
    context.font = '28px Avenir Next'
    context.fillStyle = '#5c6f64'
    context.fillText('E2E mock canvas', 48, 140)
    return canvas
  }

  const { default: html2canvas } = await import('html2canvas')
  return html2canvas(element, {
    backgroundColor: '#f7f1e3',
    scale: 2,
    useCORS: true,
    logging: false
  })
}

function triggerDownload(dataUrl: string, filename: string): void {
  const link = document.createElement('a')
  link.href = dataUrl
  link.download = filename
  link.click()
}

export async function exportElementAsImage(element: HTMLElement, filename: string): Promise<void> {
  const canvas = await buildCanvas(element)
  triggerDownload(canvas.toDataURL('image/png'), filename)
}

export async function exportElementAsPdf(element: HTMLElement, filename: string): Promise<void> {
  if (window.__TRAVEL_AGENT_E2E__) {
    triggerDownload('data:application/pdf;base64,ZWVl', filename)
    return
  }

  const { default: jsPDF } = await import('jspdf')
  const canvas = await buildCanvas(element)
  const imageData = canvas.toDataURL('image/png')
  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  })
  const width = 210
  const height = (canvas.height * width) / canvas.width

  let heightLeft = height
  let position = 0

  pdf.addImage(imageData, 'PNG', 0, position, width, height)
  heightLeft -= 297

  while (heightLeft > 0) {
    position = heightLeft - height
    pdf.addPage()
    pdf.addImage(imageData, 'PNG', 0, position, width, height)
    heightLeft -= 297
  }

  pdf.save(filename)
}
