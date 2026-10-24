import os
import sys
from build_step1_cover_toc import build_pdf
from doc_part1 import add_chapters_1_to_5
from doc_part2 import add_chapters_6_to_10
from doc_part3 import add_chapters_11_to_15
from doc_part4 import add_chapters_16_to_20
from doc_part5 import add_chapters_21_to_23
from doc_part6 import add_chapters_24_to_28
from doc_part7 import add_chapters_29_to_34
from doc_part8 import add_chapters_35_to_38
from doc_part9 import add_chapters_39_to_40
from doc_appendices import add_appendices

def main():
    print("Building cover and TOC...")
    pdf = build_pdf()
    
    print("Adding Chapters 1 to 5...")
    add_chapters_1_to_5(pdf)
    
    print("Adding Chapters 6 to 10...")
    add_chapters_6_to_10(pdf)
    
    print("Adding Chapters 11 to 15...")
    add_chapters_11_to_15(pdf)
    
    print("Adding Chapters 16 to 20...")
    add_chapters_16_to_20(pdf)
    
    print("Adding Chapters 21 to 23...")
    add_chapters_21_to_23(pdf)
    
    print("Adding Chapters 24 to 28...")
    add_chapters_24_to_28(pdf)
    
    print("Adding Chapters 29 to 34...")
    add_chapters_29_to_34(pdf)
    
    print("Adding Chapters 35 to 38...")
    add_chapters_35_to_38(pdf)
    
    print("Adding Chapters 39 to 40...")
    add_chapters_39_to_40(pdf)
    
    print("Adding Appendices A and B...")
    add_appendices(pdf)
    
    output_path = r"d:\Projects Final\Revora\fastapi-project-main\Revora_Complete_System_Explanation_50P.pdf"
    pdf.output(output_path)
    print(f"Compilation finished! Output written to: {output_path}")
    print(f"Total Pages Generated: {pdf.page_no()}")

if __name__ == '__main__':
    main()
