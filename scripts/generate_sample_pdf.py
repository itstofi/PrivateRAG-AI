from pathlib import Path

import fitz


def main() -> None:
    output = Path("sample_documents/fictional_employment_policy.pdf")
    document = fitz.open()
    pages = [
        (
            "FICTIONAL DOCUMENT — FOR DEMONSTRATION ONLY\n\n"
            "Northstar Workshop Employment Policy\n\n"
            "This original sample describes an imaginary organization. It is not legal advice.\n\n"
            "Working pattern\n"
            "The standard working week is 37.5 hours. Team members arrange their normal "
            "schedule with their manager."
        ),
        (
            "FICTIONAL DOCUMENT — FOR DEMONSTRATION ONLY\n\n"
            "Community participation\n\n"
            "Each employee receives two paid volunteer days per calendar year. Volunteer "
            "time must support a registered community organization and should be requested "
            "at least ten working days in advance.\n\n"
            "Learning allowance\n"
            "The annual learning allowance is 600 fictional credits."
        ),
    ]
    for content in pages:
        page = document.new_page(width=595, height=842)
        page.insert_textbox(
            fitz.Rect(72, 72, 523, 770),
            content,
            fontsize=12,
            fontname="helv",
            lineheight=1.4,
        )
    document.set_metadata(
        {
            "title": "Fictional Employment Policy",
            "author": "PrivateRAG AI Contributors",
            "subject": "Original fictional sample",
        }
    )
    document.save(output)
    document.close()
    print(output)


if __name__ == "__main__":
    main()
