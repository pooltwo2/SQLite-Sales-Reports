import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from tkinter import Tk, simpledialog, filedialog
import locale

# 1. Ocultar ventana principal
Tk().withdraw()

# 2. Pedir nombre de la tabla y número de mes
nombre_tabla = simpledialog.askstring("Nombre de tabla", "Ingrese el nombre de la tabla de ventas:")
mes_num = simpledialog.askinteger("Mes a mostrar", "Ingrese el número del mes (1-12) a mostrar:")

# 3. Conectar a la base de datos
ruta_db = filedialog.askopenfilename(title="Selecciona la base de datos SQLite", filetypes=[("SQLite DB", "*.db")])
try:
    conn = sqlite3.connect(ruta_db)
    cursor = conn.cursor()
except sqlite3.Error as e:
    print(f"❌ Error al conectar con la base de datos: {e}")
    exit()

# 4. Verificar columnas necesarias
cursor.execute(f"PRAGMA table_info({nombre_tabla})")
columnas = [col[1] for col in cursor.fetchall()]
requeridas = {"fecha", "precio_unitario", "cantidad"}
if not requeridas.issubset(columnas):
    print("❌ La tabla no contiene las columnas necesarias: fecha, precio_unitario, cantidad")
    conn.close()
    exit()

# 5. Consulta de ventas por día para el mes seleccionado
query_dias = f"""
    SELECT fecha, SUM(cantidad * precio_unitario) AS total
    FROM {nombre_tabla}
    WHERE strftime('%m', fecha) = ?
    GROUP BY fecha
    ORDER BY fecha;
"""
cursor.execute(query_dias, (f"{mes_num:02d}",))
datos_dias = cursor.fetchall()

# 6. Consulta de ventas totales por mes
query_meses = f"""
    SELECT strftime('%m', fecha) AS mes, SUM(cantidad * precio_unitario) AS total
    FROM {nombre_tabla}
    GROUP BY mes
    ORDER BY mes;
"""
df_meses = pd.read_sql_query(query_meses, conn)
conn.close()

# 7. Preparar DataFrame de días y sumar total del mes
df_dias = pd.DataFrame(datos_dias, columns=["fecha", "total"])
df_dias["fecha"] = pd.to_datetime(df_dias["fecha"], errors="coerce").dt.strftime("%d/%m/%Y")
total_mes = df_dias["total"].sum()
df_dias.loc[len(df_dias)] = ["Total del mes", total_mes]

# 8. Configurar idioma español para nombres de meses
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    locale.setlocale(locale.LC_TIME, 'es_VE.UTF-8')

# 9. Crear gráfico de ventas por mes
df_meses["mes"] = df_meses["mes"].apply(lambda m: pd.to_datetime(f"2025-{m}-01").strftime("%B"))
plt.figure(figsize=(10,6))
plt.barh(df_meses["mes"], df_meses["total"])
plt.xlabel("Ventas ($)")
plt.ylabel("Mes")
plt.title("Ventas por Mes")
plt.tight_layout()
grafico_path = "grafico_mensual.png"
plt.savefig(grafico_path)
plt.close()

# 10. Preguntar dónde guardar el PDF
ruta_pdf = filedialog.asksaveasfilename(
    defaultextension=".pdf",
    filetypes=[("PDF files", "*.pdf")],
    title="Guardar reporte PDF"
)

df_dias["total"] = df_dias["total"].round(2)
df_meses["total"] = df_meses["total"].round(2)


# 11. Generar PDF con tabla y gráfica
if ruta_pdf:
    doc = SimpleDocTemplate(ruta_pdf, pagesize=A4)
    estilos = getSampleStyleSheet()
    elementos = []

    nombre_mes = pd.to_datetime(f"2025-{mes_num:02d}-01").strftime("%B").capitalize()
    elementos.append(Paragraph(f"Reporte de Ventas — {nombre_mes}", estilos["Title"]))
    elementos.append(Spacer(1, 20))

    elementos.append(Paragraph("Ventas por Día", estilos["Heading2"]))
    tabla_dias = Table([df_dias.columns.tolist()] + df_dias.values.tolist(), colWidths=[200, 200])
    tabla_dias.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightblue),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))
    elementos.append(tabla_dias)
    elementos.append(Spacer(1, 20))

    elementos.append(Paragraph("Ventas Totales por Mes", estilos["Heading2"]))
    elementos.append(Image(grafico_path, width=500, height=300))

    doc.build(elementos)
    print(f"✅ PDF generado correctamente en:\n{ruta_pdf}")
else:
    print("❌ No se guardó el archivo PDF")
