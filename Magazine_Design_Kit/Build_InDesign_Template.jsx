// InDesign ExtendScript (JavaScript) Template Generator
// Textbook: Programming and Artificial Intelligence (Magazine Style Layout)
// Run this script in Adobe InDesign via: File -> Scripts -> Other Scripts (or Scripts Panel)

#target indesign

function createMagazineTemplate() {
    var doc = app.documents.add();
    
    // Document Preferences: Facing pages, A4 size
    with(doc.documentPreferences) {
        pageHeight = "297mm";
        pageWidth = "210mm";
        facingPages = true;
        pagesPerDocument = 2;
    }
    
    // Set Margins & Columns (Magazine style 2-column or 3-column layout)
    var marginPref = doc.marginPreferences;
    marginPref.top = "18mm";
    marginPref.bottom = "20mm";
    marginPref.left = "18mm";
    marginPref.right = "18mm";
    marginPref.columnCount = 2;
    marginPref.columnGutter = "5mm";

    // Setup Color Swatches
    function getOrCreateColor(name, vals) {
        var c = doc.colors.itemByName(name);
        if (!c.isValid) {
            c = doc.colors.add({
                name: name,
                model: ColorModel.PROCESS,
                space: ColorSpace.CMYK,
                colorValue: vals
            });
        }
        return c;
    }

    var brandPrimary = getOrCreateColor("Brand_Primary_Blue", [80, 50, 0, 0]);
    var brandAccent = getOrCreateColor("Brand_Magenta", [0, 95, 20, 0]);
    var brandDark = getOrCreateColor("Brand_Dark_Slate", [80, 60, 40, 50]);
    var lightBgColor = getOrCreateColor("Light_Blue_Tint", [8, 2, 0, 0]);
    var warningAmber = getOrCreateColor("Warning_Amber", [0, 40, 90, 0]);

    // Setup Paragraph Styles
    function addParaStyle(name, props) {
        var s = doc.paragraphStyles.itemByName(name);
        if (!s.isValid) {
            s = doc.paragraphStyles.add({name: name});
        }
        for (var p in props) {
            s[p] = props[p];
        }
        return s;
    }

    var kickerStyle = addParaStyle("01_Kicker", {
        pointSize: 10,
        fillColor: brandAccent,
        capitalization: Capitalization.ALL_CAPS,
        spaceAfter: "3mm"
    });

    var titleStyle = addParaStyle("02_Lesson_Headline", {
        pointSize: 26,
        leading: 30,
        fillColor: brandDark,
        fontStyle: "Bold",
        spaceAfter: "6mm"
    });

    var leadStyle = addParaStyle("03_Lead_Paragraph", {
        pointSize: 12,
        leading: 16,
        fillColor: brandDark,
        fontStyle: "Bold",
        spaceAfter: "5mm"
    });

    var bodyStyle = addParaStyle("04_Body_Text", {
        pointSize: 9.5,
        leading: 13.5,
        fillColor: brandDark,
        spaceAfter: "3mm"
    });

    var mascotCalloutStyle = addParaStyle("05_Mascot_Callout_Text", {
        pointSize: 9,
        leading: 13,
        fillColor: brandDark,
        fontStyle: "Italic"
    });

    var questionHeaderStyle = addParaStyle("06_Question_Prompt", {
        pointSize: 11,
        leading: 15,
        fillColor: brandDark,
        fontStyle: "Bold",
        spaceAfter: "3mm"
    });

    var mcqChoiceStyle = addParaStyle("07_MCQ_Choice", {
        pointSize: 9.5,
        leading: 14,
        fillColor: brandDark,
        leftIndent: "8mm",
        firstLineIndent: "-8mm",
        spaceAfter: "2mm"
    });

    // Setup Object Styles for Containers & Callouts
    function addObjectStyle(name, props) {
        var s = doc.objectStyles.itemByName(name);
        if (!s.isValid) {
            s = doc.objectStyles.add({name: name});
        }
        for (var p in props) {
            s[p] = props[p];
        }
        return s;
    }

    var mascotBoxStyle = addObjectStyle("Mascot_Box_Container", {
        fillColor: lightBgColor,
        strokeColor: brandPrimary,
        strokeWeight: 1,
        bottomLeftCornerOption: CornerOptions.ROUNDED_CORNER,
        bottomRightCornerOption: CornerOptions.ROUNDED_CORNER,
        topLeftCornerOption: CornerOptions.ROUNDED_CORNER,
        topRightCornerOption: CornerOptions.ROUNDED_CORNER,
        topLeftCornerRadius: "4mm",
        bottomLeftCornerRadius: "4mm",
        topRightCornerRadius: "4mm",
        bottomRightCornerRadius: "4mm"
    });

    alert("Meezan Magazine InDesign Template setup is complete!\n- 7 Paragraph Styles added\n- Custom Swatches added\n- Double Page Spread configured.");
}

createMagazineTemplate();
