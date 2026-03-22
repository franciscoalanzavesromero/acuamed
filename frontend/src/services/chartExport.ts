import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'

export const exportChartToPNG = async (
  chartElementId: string,
  filename: string = 'chart.png'
): Promise<void> => {
  const element = document.getElementById(chartElementId)
  if (!element) {
    throw new Error(`Element with id '${chartElementId}' not found`)
  }

  try {
    const canvas = await html2canvas(element, {
      backgroundColor: '#ffffff',
      scale: 2, // Higher quality
      useCORS: true,
    })

    const link = document.createElement('a')
    link.download = filename
    link.href = canvas.toDataURL('image/png')
    link.click()
  } catch (error) {
    console.error('Error exporting chart to PNG:', error)
    throw new Error('Failed to export chart to PNG')
  }
}

export const exportChartToPDF = async (
  chartElementId: string,
  filename: string = 'chart.pdf'
): Promise<void> => {
  const element = document.getElementById(chartElementId)
  if (!element) {
    throw new Error(`Element with id '${chartElementId}' not found`)
  }

  try {
    const canvas = await html2canvas(element, {
      backgroundColor: '#ffffff',
      scale: 2,
      useCORS: true,
    })

    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF({
      orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
      unit: 'px',
      format: [canvas.width, canvas.height],
    })

    pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height)
    pdf.save(filename)
  } catch (error) {
    console.error('Error exporting chart to PDF:', error)
    throw new Error('Failed to export chart to PDF')
  }
}

export const exportMultipleChartsToPDF = async (
  chartElementIds: string[],
  filename: string = 'report.pdf'
): Promise<void> => {
  if (chartElementIds.length === 0) {
    throw new Error('No chart elements provided')
  }

  try {
    const pdf = new jsPDF({
      orientation: 'landscape',
      unit: 'mm',
      format: 'a4',
    })

    for (let i = 0; i < chartElementIds.length; i++) {
      const element = document.getElementById(chartElementIds[i])
      if (!element) continue

      if (i > 0) {
        pdf.addPage()
      }

      const canvas = await html2canvas(element, {
        backgroundColor: '#ffffff',
        scale: 2,
        useCORS: true,
      })

      const imgData = canvas.toDataURL('image/png')
      const pageWidth = pdf.internal.pageSize.getWidth()
      const pageHeight = pdf.internal.pageSize.getHeight()
      
      const imgWidth = pageWidth - 20 // 10mm margin each side
      const imgHeight = (canvas.height * imgWidth) / canvas.width
      
      const finalHeight = Math.min(imgHeight, pageHeight - 20)
      
      pdf.addImage(imgData, 'PNG', 10, 10, imgWidth, finalHeight)
    }

    pdf.save(filename)
  } catch (error) {
    console.error('Error exporting charts to PDF:', error)
    throw new Error('Failed to export charts to PDF')
  }
}
