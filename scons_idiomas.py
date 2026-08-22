# -*- coding: utf-8 -*-
# scons_recursos.py
#
# Script para compilar archivos .po a .mo, generar manifest.ini traducidos,
# convertir documentación .md a .html y generar metadatos localmente.
# Compatible con el sistema de ActualizadorRecursos.
#
# Uso independiente:
#   python scons_recursos.py
#   python scons_recursos.py --directorio-idiomas addon/locale
#   python scons_recursos.py --solo-idiomas
#   python scons_recursos.py --solo-docs
#
# Uso con SCons (añadir al sconstruct):
#   import scons_recursos
#   scons_recursos.integrarConSCons(env)
#
# Licencia: GPL v2

import os
import re
import sys
import subprocess
import hashlib
import json
import codecs
import shutil
from datetime import datetime, timezone


DIR_BASE = os.path.dirname(os.path.abspath(__file__))
DIR_LOCALE = os.path.join(DIR_BASE, "addon", "locale")
DIR_DOC = os.path.join(DIR_BASE, "addon", "doc")
ARCHIVO_INFO = "recursos_info.json"


def buscarMsgfmt() -> str:
	"""
	Busca el ejecutable msgfmt en el sistema.
	
	Returns:
		str: Ruta al ejecutable msgfmt.
	
	Raises:
		FileNotFoundError: Si no se encuentra msgfmt.
	"""
	try:
		resultado = subprocess.run(
			["msgfmt", "--version"], capture_output=True, text=True,
		)
		if resultado.returncode == 0:
			return "msgfmt"
	except FileNotFoundError:
		pass
	
	rutas_posibles = [
		os.path.join(os.environ.get("ProgramFiles", ""), "gettext", "bin", "msgfmt.exe"),
		os.path.join(os.environ.get("ProgramFiles(x86)", ""), "gettext", "bin", "msgfmt.exe"),
		os.path.join(os.environ.get("ProgramFiles", ""), "Git", "usr", "bin", "msgfmt.exe"),
		r"C:\msys64\usr\bin\msgfmt.exe",
	]
	
	for ruta in rutas_posibles:
		if os.path.exists(ruta):
			return ruta
	
	raise FileNotFoundError(
		"No se encontró 'msgfmt'. Instala gettext:\n"
		"  Windows: https://mlocati.github.io/articles/gettext-iconv-windows.html\n"
		"  Linux:   sudo apt-get install gettext\n"
		"  Mac:     brew install gettext"
	)


def compilarPO(ruta_po: str, ruta_mo: str, msgfmt: str = "msgfmt") -> bool:
	"""Compila un archivo .po a .mo."""
	os.makedirs(os.path.dirname(ruta_mo), exist_ok=True)
	try:
		r = subprocess.run([msgfmt, "-o", ruta_mo, ruta_po], capture_output=True, text=True)
		if r.returncode != 0:
			print(f"  ✗ Error: {r.stderr.strip()}")
			return False
		return True
	except Exception as e:
		print(f"  ✗ Excepción: {e}")
		return False


def generarManifestTraducido(
	ruta_mo: str,
	ruta_manifest: str,
	ruta_plantilla: str,
	addon_info: dict,
) -> bool:
	"""
	Genera manifest.ini traducido usando el archivo .mo y la plantilla.
	
	Replica la lógica de NVDATool/manifests.py:generateTranslatedManifest()
	para poder ejecutarse sin SCons.
	
	Args:
		ruta_mo: Ruta al archivo .mo compilado.
		ruta_manifest: Ruta de salida del manifest.ini.
		ruta_plantilla: Ruta a manifest-translated.ini.tpl.
		addon_info: Diccionario con addon_summary, addon_description, addon_changelog.
	
	Returns:
		True si se generó correctamente.
	"""
	import gettext as _gt
	
	try:
		with open(ruta_mo, "rb") as f:
			_ = _gt.GNUTranslations(f).gettext
		
		vars_trad = {}
		for var in ("addon_summary", "addon_description", "addon_changelog"):
			vars_trad[var] = _(addon_info[var])
		
		with codecs.open(ruta_plantilla, "r", "utf-8") as f:
			plantilla = f.read()
		
		manifest = plantilla.format(**vars_trad)
		
		os.makedirs(os.path.dirname(ruta_manifest), exist_ok=True)
		with codecs.open(ruta_manifest, "w", "utf-8") as f:
			f.write(manifest)
		
		return True
	except Exception as e:
		print(f"  ✗ Error generando manifest: {e}")
		return False


def convertirMdAHtml(
	ruta_md: str,
	ruta_html: str,
	addon_info: dict,
	ruta_mo: str = None,
	extensiones_md: list = None,
) -> bool:
	"""
	Convierte un archivo Markdown a HTML con el formato NVDA.
	
	Replica la lógica de NVDATool/docs.py:md2html() para poder
	ejecutarse sin SCons.
	
	Args:
		ruta_md: Ruta al archivo .md de entrada.
		ruta_html: Ruta del archivo .html de salida.
		addon_info: Diccionario con addon_summary, addon_version.
		ruta_mo: Ruta al .mo para traducir el título (opcional).
		extensiones_md: Lista de extensiones markdown (ej: ["markdown.extensions.tables"]).
	
	Returns:
		True si se convirtió correctamente.
	"""
	import gettext as _gt
	
	try:
		import markdown as _md
	except ImportError:
		print("  ⚠ No se encontró 'markdown'. Instala: pip install markdown")
		return False
	
	if extensiones_md is None:
		extensiones_md = []
	
	try:
		# Obtener título traducido
		if ruta_mo and os.path.exists(ruta_mo):
			try:
				with open(ruta_mo, "rb") as f:
					_ = _gt.GNUTranslations(f).gettext
				summary = _(addon_info["addon_summary"])
			except Exception:
				summary = addon_info["addon_summary"]
		else:
			summary = addon_info["addon_summary"]
		
		version = addon_info["addon_version"]
		title = f"{summary} {version}"
		lang = os.path.basename(os.path.dirname(ruta_md)).replace("_", "-")
		
		# Reemplazos de cabecera ikiwiki
		header_dic = {
			'[[!meta title="': "# ",
			'"]]': " #",
		}
		
		with open(ruta_md, "r", encoding="utf-8") as f:
			md_text = f.read()
		
		for k, v in header_dic.items():
			md_text = md_text.replace(k, v, 1)
		
		html_text = _md.markdown(md_text, extensions=extensiones_md)
		
		doc_text = "\n".join((
			"<!DOCTYPE html>",
			f'<html lang="{lang}">',
			"<head>",
			'<meta charset="UTF-8">',
			'<meta name="viewport" content="width=device-width, initial-scale=1.0">',
			'<link rel="stylesheet" type="text/css" href="../style.css" media="screen">',
			f"<title>{title}</title>",
			"</head>\n<body>",
			html_text,
			"</body>\n</html>",
		))
		
		os.makedirs(os.path.dirname(ruta_html), exist_ok=True)
		with open(ruta_html, "w", encoding="utf-8") as f:
			f.write(doc_text)
		
		return True
	except Exception as e:
		print(f"  ✗ Error convirtiendo MD a HTML: {e}")
		return False


def hashDirectorio(directorio: str, extensiones: list) -> list:
	"""Calcula hashes SHA-256 de archivos filtrados por extensión."""
	resultados = []
	if not os.path.exists(directorio):
		return resultados
	for raiz, _, archivos in os.walk(directorio):
		for archivo in sorted(archivos):
			if any(archivo.endswith(ext) for ext in extensiones):
				ruta = os.path.join(raiz, archivo)
				h = hashlib.sha256(open(ruta, "rb").read()).hexdigest()
				rel = os.path.relpath(ruta, directorio).replace(os.sep, "/")
				resultados.append(f"{h}  {rel}")
	return resultados


def generarMetadatos(
	dir_locale: str = DIR_LOCALE,
	dir_doc: str = DIR_DOC,
	nombre: str = "",
	ext_idiomas: list = None,
	ext_docs: list = None,
) -> dict:
	"""
	Genera metadatos combinados de idiomas y documentación.
	
	Args:
		dir_locale: Directorio de locales.
		dir_doc: Directorio de documentación.
		nombre: Nombre del complemento.
		ext_idiomas: Extensiones de archivos de idiomas.
		ext_docs: Extensiones de archivos de documentación.
	
	Returns:
		dict con hash_combinado, fecha, idiomas_locale, idiomas_doc.
	"""
	if ext_idiomas is None:
		ext_idiomas = [".mo", ".po", ".ini"]
	if ext_docs is None:
		ext_docs = [".html", ".md", ".txt", ".css"]
	
	hashes = []
	idiomas_locale = set()
	idiomas_doc = set()
	
	# Archivos de idiomas
	for item in hashDirectorio(dir_locale, ext_idiomas):
		hashes.append(f"locale/{item.split('  ', 1)[1]}")
		hashes.append(item)
		partes = item.split("  ", 1)[1].split("/")
		if partes:
			idiomas_locale.add(partes[0])
	
	# Archivos de documentación
	for item in hashDirectorio(dir_doc, ext_docs):
		hashes.append(f"doc/{item.split('  ', 1)[1]}")
		hashes.append(item)
		partes = item.split("  ", 1)[1].split("/")
		if partes:
			idiomas_doc.add(partes[0])
	
	contenido = "\n".join(sorted(hashes))
	hash_total = hashlib.sha256(contenido.encode()).hexdigest() if hashes else ""
	
	return {
		"hash_combinado": hash_total,
		"fecha": datetime.now(timezone.utc).isoformat(),
		"complemento": nombre,
		"idiomas_locale": sorted(idiomas_locale),
		"idiomas_doc": sorted(idiomas_doc),
	}


def _cargarBuildVars(dir_base: str = DIR_BASE) -> dict:
	"""
	Carga buildVars.py del proyecto de forma segura,
	sin depender de SCons instalado.
	
	Returns:
		Diccionario con addon_info, markdownExtensions, baseLanguage.
		Retorna None si no se encuentra buildVars.py.
	"""
	ruta_buildvars = os.path.join(dir_base, "buildVars.py")
	if not os.path.exists(ruta_buildvars):
		return None
	
	import types
	# Mock de SCons para que buildVars pueda importarse
	for mod in ['SCons', 'SCons.Script', 'SCons.Node', 'SCons.Node.FS']:
		if mod not in sys.modules:
			sys.modules[mod] = types.ModuleType(mod)
	m = sys.modules['SCons.Script']
	for attr in ['EnsurePythonVersion', 'Variables', 'BoolVariable', 'Environment', 'Copy', 'Builder']:
		if not hasattr(m, attr):
			setattr(m, attr, lambda *a, **kw: None)
	
	if dir_base not in sys.path:
		sys.path.insert(0, dir_base)
	
	try:
		import buildVars
		return {
			"addon_info": dict(buildVars.addon_info),
			"markdownExtensions": getattr(buildVars, 'markdownExtensions', []),
			"baseLanguage": getattr(buildVars, 'baseLanguage', 'en'),
		}
	except Exception as e:
		print(f"  ⚠ No se pudo importar buildVars.py: {e}")
		return None


def construirEtiquetaRecursos(
	addon_version: str = None,
	tag_release: str = None,
	dir_base: str = DIR_BASE,
) -> str:
	"""
	Construye la etiqueta de recursos a partir de la versión del addon.

	Si se proporciona una etiqueta explícita, se respeta. Si no, intenta
	obtener la versión desde buildVars.py del repositorio, extrae los
	dos primeros componentes numéricos (ej: '2026.1.2' -> '2026.1')
	para formar una etiqueta del estilo 'recursos_2026.1'.
	Si no es posible, usa 'recursos-latest'.
	"""
	if tag_release:
		return tag_release

	if addon_version is None:
		build_vars = _cargarBuildVars(dir_base)
		if build_vars:
			addon_info = build_vars.get("addon_info", {})
			addon_version = addon_info.get("addon_version")

	if addon_version is None:
		return "recursos-latest"

	version_str = str(addon_version).strip()
	if not version_str:
		return "recursos-latest"

	# Extraer componentes numéricos (ej: 2026.1.2 -> 2026.1)
	partes = re.findall(r"\d+", version_str)
	if not partes:
		return "recursos-latest"
	
	version_formateada = ".".join(partes[:2])
	return f"recursos_{version_formateada}"


def compilarRecursos(
	dir_locale: str = None,
	dir_doc: str = None,
	nombre: str = "",
	generar_info: bool = True,
	compilar_po: bool = True,
	generar_manifest: bool = True,
	generar_html: bool = True,
) -> tuple:
	"""
	Compila todos los .po a .mo, genera manifest.ini traducidos,
	convierte .md a .html y genera metadatos.
	
	Args:
		dir_locale: Directorio de locales (defecto: addon/locale).
		dir_doc: Directorio de documentación (defecto: addon/doc).
		nombre: Nombre del complemento para metadatos.
		generar_info: Si True, genera el archivo recursos_info.json.
		compilar_po: Si True, compila archivos .po a .mo.
		generar_manifest: Si True, genera manifest.ini traducidos por idioma.
		generar_html: Si True, convierte archivos .md a .html.
	
	Returns:
		(compilados, errores): Conteo de resultados.
	"""
	if dir_locale is None:
		dir_locale = DIR_LOCALE
	if dir_doc is None:
		dir_doc = DIR_DOC
	
	print("=" * 60)
	print("  Compilación de recursos para complemento NVDA")
	print("=" * 60)
	
	compilados = 0
	errores = 0
	
	# ── Compilar .po a .mo ──
	if compilar_po and os.path.exists(dir_locale):
		try:
			msgfmt = buscarMsgfmt()
			print(f"\nUsando msgfmt: {msgfmt}")
		except FileNotFoundError as e:
			print(f"\nERROR: {e}")
			return (0, 1)
		
		print(f"Directorio de idiomas: {dir_locale}\n")
		
		for raiz, _, archivos in os.walk(dir_locale):
			for archivo in sorted(archivos):
				if archivo.endswith(".po"):
					ruta_po = os.path.join(raiz, archivo)
					ruta_mo = os.path.join(raiz, os.path.splitext(archivo)[0] + ".mo")
					rel = os.path.relpath(ruta_po, dir_locale)
					print(f"Compilando: {rel}")
					if compilarPO(ruta_po, ruta_mo, msgfmt):
						compilados += 1
						print(f"  ✓ OK ({os.path.getsize(ruta_mo):,} bytes)")
					else:
						errores += 1
	
	# ── Cargar buildVars para manifest.ini y HTML ──
	build_vars = None
	if generar_manifest or generar_html:
		build_vars = _cargarBuildVars()
		if build_vars is None:
			print("\n⚠ No se encontró buildVars.py, omitiendo manifest.ini y HTML")
			generar_manifest = False
			generar_html = False
	
	# ── Generar manifest.ini traducidos ──
	if generar_manifest and os.path.exists(dir_locale) and build_vars:
		plantilla = os.path.join(DIR_BASE, "manifest-translated.ini.tpl")
		if os.path.exists(plantilla):
			print(f"\n{'─' * 60}")
			print("Generando manifest.ini traducidos...")
			manifest_ok = 0
			manifest_err = 0
			
			for lang in sorted(os.listdir(dir_locale)):
				lang_path = os.path.join(dir_locale, lang)
				if not os.path.isdir(lang_path):
					continue
				mo_path = os.path.join(lang_path, "LC_MESSAGES", "nvda.mo")
				if not os.path.exists(mo_path):
					continue
				
				dest = os.path.join(lang_path, "manifest.ini")
				print(f"  {lang}/manifest.ini")
				if generarManifestTraducido(mo_path, dest, plantilla, build_vars["addon_info"]):
					manifest_ok += 1
					print(f"    ✓ OK")
				else:
					manifest_err += 1
			
			print(f"Manifest: {manifest_ok} generados, {manifest_err} errores")
		else:
			print(f"\n⚠ No se encontró {plantilla}, omitiendo manifest.ini")
	
	# ── Generar HTML desde Markdown ──
	if generar_html and os.path.exists(dir_doc) and build_vars:
		# Copiar style.css a addon/doc/ si existe en la raíz
		style_src = os.path.join(DIR_BASE, "style.css")
		if os.path.exists(style_src):
			style_dst = os.path.join(dir_doc, "style.css")
			shutil.copy2(style_src, style_dst)
			print(f"\n✓ style.css copiado a {os.path.relpath(style_dst, DIR_BASE)}")
		
		# Copiar readme.md raíz a addon/doc/{baseLanguage}/
		readme_src = os.path.join(DIR_BASE, "readme.md")
		base_lang = build_vars["baseLanguage"]
		if os.path.exists(readme_src):
			dest_dir = os.path.join(dir_doc, base_lang)
			os.makedirs(dest_dir, exist_ok=True)
			shutil.copy2(readme_src, os.path.join(dest_dir, "readme.md"))
			print(f"✓ readme.md copiado a addon/doc/{base_lang}/")
		
		# Mapear .mo por idioma
		mo_por_idioma = {}
		if os.path.isdir(dir_locale):
			for lang in os.listdir(dir_locale):
				mo = os.path.join(dir_locale, lang, "LC_MESSAGES", "nvda.mo")
				if os.path.exists(mo):
					mo_por_idioma[lang] = mo
		
		print(f"\n{'─' * 60}")
		print("Generando HTML desde Markdown...")
		html_ok = 0
		html_err = 0
		md_ext = build_vars["markdownExtensions"]
		
		for lang_dir in sorted(os.listdir(dir_doc)):
			lang_path = os.path.join(dir_doc, lang_dir)
			if not os.path.isdir(lang_path):
				continue
			for fname in sorted(os.listdir(lang_path)):
				if not fname.endswith(".md"):
					continue
				md_path = os.path.join(lang_path, fname)
				html_path = os.path.join(lang_path, fname.rsplit(".", 1)[0] + ".html")
				mo_path = mo_por_idioma.get(lang_dir)
				
				print(f"  {lang_dir}/{fname} → .html")
				if convertirMdAHtml(md_path, html_path, build_vars["addon_info"], mo_path, md_ext):
					html_ok += 1
					print(f"    ✓ OK")
				else:
					html_err += 1
		
		print(f"HTML: {html_ok} generados, {html_err} errores")
	
	# Resumen de documentación
	if os.path.exists(dir_doc):
		n_docs = sum(
			1 for r, _, fs in os.walk(dir_doc)
			for f in fs if f.endswith((".html", ".md", ".txt"))
		)
		print(f"\nDocumentación total: {n_docs} archivos")
	
	print(f"\n{'─' * 60}")
	print(f"Traducciones: {compilados} compiladas, {errores} errores")
	print(f"{'─' * 60}")
	
	# Generar metadatos
	if generar_info:
		print("\nGenerando metadatos...")
		meta = generarMetadatos(dir_locale, dir_doc, nombre)
		ruta_info = os.path.join(os.path.dirname(dir_locale), ARCHIVO_INFO)
		with open(ruta_info, "w", encoding="utf-8") as f:
			json.dump(meta, f, ensure_ascii=False, indent="\t")
		print(f"  Hash: {meta['hash_combinado']}")
		print(f"  Idiomas (locale): {', '.join(meta['idiomas_locale']) or 'ninguno'}")
		print(f"  Idiomas (doc): {', '.join(meta['idiomas_doc']) or 'ninguno'}")
		print(f"  Archivo: {ruta_info}")
	
	return (compilados, errores)


def integrarConSCons(env):
	"""
	Integra la compilación con SCons. Añadir al sconstruct:
		import scons_recursos
		scons_recursos.integrarConSCons(env)
	"""
	try:
		sys.path.insert(0, DIR_BASE)
		import buildVars
		nombre = buildVars.addon_info.get("addon_name", "")
	except ImportError:
		nombre = ""
	
	compilarRecursos(nombre=nombre)


if __name__ == "__main__":
	import argparse
	
	parser = argparse.ArgumentParser(
		description="Compilar recursos (.po → .mo, manifest.ini, .md → .html) y generar metadatos",
	)
	parser.add_argument("--directorio-idiomas", "-i", default=DIR_LOCALE)
	parser.add_argument("--directorio-docs", "-d", default=DIR_DOC)
	parser.add_argument("--nombre", "-n", default="")
	parser.add_argument("--sin-info", action="store_true", help="No generar metadatos")
	parser.add_argument("--solo-idiomas", action="store_true", help="Solo compilar idiomas")
	parser.add_argument("--solo-docs", action="store_true", help="Solo generar documentación HTML")
	parser.add_argument("--sin-manifest", action="store_true", help="No generar manifest.ini traducidos")
	parser.add_argument("--sin-html", action="store_true", help="No generar HTML desde Markdown")
	
	args = parser.parse_args()
	
	compilados, errores = compilarRecursos(
		dir_locale=args.directorio_idiomas,
		dir_doc=args.directorio_docs,
		nombre=args.nombre,
		generar_info=not args.sin_info,
		compilar_po=not args.solo_docs,
		generar_manifest=not args.sin_manifest and not args.solo_docs,
		generar_html=not args.sin_html and not args.solo_idiomas,
	)
	
	sys.exit(1 if errores > 0 else 0)
