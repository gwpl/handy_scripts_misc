#!/usr/bin/env python

import qrcode
import warnings
from fpdf import FPDF
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
import os

# Ignore deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Required dependencies:
# pip install qrcode[pil] fpdf2 svglib

def generate_qr_code(ssid, password):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr_data = f"WIFI:T:WPA;S:{ssid};P:{password};;"
    qr.add_data(qr_data)
    qr.make(fit=True)
    img_file = f'wifi_{ssid}_qr_code.png'
    img = qr.make_image(fill='black', back_color='white')
    img.save(img_file)

def create_sticker(ssid, password):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, f'WiFi: {ssid}', 0, 1)
    pdf.cell(0, 10, f'Password: {password}', 0, 1)
    img_file=f'wifi_{ssid}_qr_code.png'
    pdf.image(img_file, x = 10, y = 30, w = 100, h = 100)
    pdf_file=f'wifi_{ssid}_sticker.pdf'
    pdf.output(pdf_file, 'F')

def main():
    ssid = input("Enter WiFi SSID: ")
    password = input("Enter WiFi Password: ")
    generate_qr_code(ssid, password)
    create_sticker(ssid, password)

if __name__ == "__main__":
    main()

