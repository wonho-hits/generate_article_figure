"""SVG symbol library for bio/chem schematics.

88 reusable symbols total: 50 hand-written (33 base + 5 signaling extensions
+ 3 cell-adhesion receptors [integrin + cadherin + mhc_complex] + 2
proteases [mmp + caspase] + 5 ECM/junction primitives [fibronectin, laminin,
proteoglycan, basement_membrane, hemidesmosome] + 2 autophagy organelles
[autophagosome, lysosome]) + 24 bundled from bioicons.com (8 cell-division
+ 6 ECM/tissue + 2 cytoskeleton + 2 trafficking + 2 oncology + 4 immunology)
+ 14 per-stage wrappers cropped from bioicons composites (6 mitosis +
8 meiosis). See [ATTRIBUTIONS.md](../../../ATTRIBUTIONS.md) for licenses.

Bundled symbols are LAZY-injected: at runtime Path A scans the LLM's emitted
SVG for `<use href="#...">` references and only the matched symbols land in
the output `<defs>` block. This means the bundled set can grow without
penalising responses that don't reference cell-division icons.

Path A's system prompt advertises this catalog; outputs reference symbols via
`<use href="#<id>" x="..." y="..." width="..." height="..."/>`.

Style conventions for hand-written symbols (BioRender-inspired):
- Receptors / membrane proteins: light blue fill (#A8C5E2), dark blue stroke (#3A5F7F)
- Cytosolic enzymes: green fill (#B5D4A8), green stroke (#4A7A3F)
- Ions / charge carriers: light purple fill (#D4B8E2), purple stroke (#7F4A9C)
- Energy currency (ATP/ADP/cAMP): warm yellow fill (#FFE8B0), amber stroke (#C8901F)
- Lipids / membrane: peach fill (#FFD4B0), orange stroke (#C86B1F)
- Modifications: bright accent (P=red, Ub=purple, Ac=green)
- Organelles: pastel fill, contrasting stroke
- Stroke-width: 1.5 baseline, 2.0 for primary outlines, 2.5 for organelle perimeter

Bundled `bioicons_*` symbols use Servier Medical Art's pink-and-pastel
biological style and ship as complete composite illustrations
(e.g. `bioicons_mitosis` is the whole mitosis cycle as one icon).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain._bioicons_data import BIOICONS
from app.domain._bioicons_subregions import BIOICONS_SUBREGIONS


@dataclass(frozen=True)
class SymbolEntry:
    id: str
    name: str
    category: str
    use_when: str
    default_w: int
    default_h: int


# ── Symbol SVG strings ────────────────────────────────────────────────────

_RECEPTORS: dict[str, str] = {
    "gpcr": """<symbol id="gpcr" viewBox="0 0 60 80" overflow="visible">
        <rect x="5" y="5" width="50" height="70" rx="6"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <path d="M 12 14 L 48 22 L 12 30 L 48 38 L 12 46 L 48 54 L 12 62 L 48 70"
              fill="none" stroke="#3A5F7F" stroke-width="1.5" opacity="0.8"/>
    </symbol>""",
    "rtk": """<symbol id="rtk" viewBox="0 0 60 100" overflow="visible">
        <rect x="10" y="5" width="40" height="32" rx="4"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <rect x="22" y="37" width="16" height="22"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <ellipse cx="30" cy="78" rx="22" ry="16"
              fill="#B5D4A8" stroke="#4A7A3F" stroke-width="2"/>
        <text x="30" y="83" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif"
              font-size="11" fill="#4A7A3F" font-weight="bold">K</text>
    </symbol>""",
    "ion_channel": """<symbol id="ion_channel" viewBox="0 0 60 80" overflow="visible">
        <rect x="3" y="5" width="22" height="70" rx="4"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <rect x="35" y="5" width="22" height="70" rx="4"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
    </symbol>""",
    "transporter": """<symbol id="transporter" viewBox="0 0 60 80" overflow="visible">
        <rect x="5" y="5" width="50" height="70" rx="6"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <path d="M 30 68 L 30 16 M 22 24 L 30 14 L 38 24"
              fill="none" stroke="#3A5F7F" stroke-width="2" stroke-linecap="round"/>
    </symbol>""",
    "generic_membrane_protein": """<symbol id="generic_membrane_protein" viewBox="0 0 60 80" overflow="visible">
        <rect x="5" y="5" width="50" height="70" rx="8"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
    </symbol>""",
    "cadherin": """<symbol id="cadherin" viewBox="0 0 32 96" overflow="visible">
        <!-- 5 extracellular cadherin (EC) domains stacked vertically -->
        <ellipse cx="16" cy="6"  rx="8" ry="5" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1.8"/>
        <ellipse cx="16" cy="16" rx="8" ry="5" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1.8"/>
        <ellipse cx="16" cy="26" rx="8" ry="5" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1.8"/>
        <ellipse cx="16" cy="36" rx="8" ry="5" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1.8"/>
        <ellipse cx="16" cy="46" rx="8" ry="5" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1.8"/>
        <!-- Transmembrane helix -->
        <rect x="11" y="56" width="10" height="22" rx="3"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1.8"/>
        <!-- Cytoplasmic tail (connects to β-catenin/actin) -->
        <line x1="16" y1="78" x2="16" y2="92"
              stroke="#3A5F7F" stroke-width="2.2" stroke-linecap="round"/>
    </symbol>""",
    "mhc_complex": """<symbol id="mhc_complex" viewBox="0 0 50 80" overflow="visible">
        <!-- Antigen-presenting molecule: transmembrane body with a top
             peptide-binding groove. Represents MHC class I or II — label
             with <text> for the specific isoform. -->
        <!-- Transmembrane body (receptor palette) -->
        <rect x="10" y="12" width="30" height="60" rx="5"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <!-- Peptide-binding groove on top (open arms) -->
        <path d="M 8 12 Q 12 2 25 4 Q 38 2 42 12"
              fill="#A8D6E2" stroke="#3A5F7F" stroke-width="2"
              stroke-linejoin="round"/>
        <!-- Bound peptide (small magenta rod sitting in the groove) -->
        <rect x="17" y="3" width="16" height="3.5" rx="1.5"
              fill="#C84A6F" stroke="#7F2F4A" stroke-width="0.8"/>
        <!-- Short cytoplasmic tail -->
        <line x1="25" y1="72" x2="25" y2="78"
              stroke="#3A5F7F" stroke-width="2.5" stroke-linecap="round"/>
    </symbol>""",
    "integrin": """<symbol id="integrin" viewBox="0 0 60 92" overflow="visible">
        <!-- Alpha subunit (left): rectangular body + small head bulge -->
        <ellipse cx="18" cy="6" rx="9" ry="6"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <rect x="10" y="10" width="16" height="68" rx="6"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="2"/>
        <text x="18" y="48" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif" font-size="11"
              fill="#3A5F7F" font-weight="bold">α</text>
        <!-- Cytoplasmic tail -->
        <line x1="18" y1="78" x2="18" y2="88"
              stroke="#3A5F7F" stroke-width="2.5" stroke-linecap="round"/>
        <!-- Beta subunit (right): slightly different tint to distinguish -->
        <ellipse cx="42" cy="6" rx="9" ry="6"
              fill="#A8D6E2" stroke="#3A6F7F" stroke-width="2"/>
        <rect x="34" y="10" width="16" height="68" rx="6"
              fill="#A8D6E2" stroke="#3A6F7F" stroke-width="2"/>
        <text x="42" y="48" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif" font-size="11"
              fill="#3A6F7F" font-weight="bold">β</text>
        <!-- Cytoplasmic tail -->
        <line x1="42" y1="78" x2="42" y2="88"
              stroke="#3A6F7F" stroke-width="2.5" stroke-linecap="round"/>
    </symbol>""",
}

_ENZYMES: dict[str, str] = {
    "kinase": """<symbol id="kinase" viewBox="0 0 80 50" overflow="visible">
        <ellipse cx="40" cy="25" rx="35" ry="20"
              fill="#B5D4A8" stroke="#4A7A3F" stroke-width="2"/>
    </symbol>""",
    "phosphatase": """<symbol id="phosphatase" viewBox="0 0 80 50" overflow="visible">
        <ellipse cx="40" cy="25" rx="35" ry="20"
              fill="#E8C5B5" stroke="#9C5F47" stroke-width="2"/>
    </symbol>""",
    "generic_protein": """<symbol id="generic_protein" viewBox="0 0 80 50" overflow="visible">
        <rect x="5" y="5" width="70" height="40" rx="20"
              fill="#D4D4D4" stroke="#666666" stroke-width="2"/>
    </symbol>""",
    "complex": """<symbol id="complex" viewBox="0 0 110 60" overflow="visible">
        <ellipse cx="30" cy="30" rx="25" ry="18"
              fill="#B5D4A8" stroke="#4A7A3F" stroke-width="2"/>
        <ellipse cx="62" cy="30" rx="25" ry="18"
              fill="#A8C5D4" stroke="#4A6F7F" stroke-width="2"/>
        <ellipse cx="88" cy="30" rx="20" ry="14"
              fill="#D4C5A8" stroke="#7F6F4A" stroke-width="2"/>
    </symbol>""",
    "mmp": """<symbol id="mmp" viewBox="0 0 50 50" overflow="visible">
        <!-- Pac-Man shape: open mouth facing right — substrate (collagen)
             enters here and is cleaved. Coral palette signals "destruction"
             / matrix remodelling. -->
        <path d="M 25 25 L 45 12 A 21 21 0 1 1 45 38 Z"
              fill="#E8978F" stroke="#9C4A47" stroke-width="2"
              stroke-linejoin="round"/>
        <!-- Catalytic Zn²⁺ centre at the active site -->
        <circle cx="22" cy="25" r="3.5"
              fill="#FFD27A" stroke="#9C7530" stroke-width="1.2"/>
        <text x="22" y="28" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif" font-size="6"
              fill="#7F4A30" font-weight="bold">Zn</text>
    </symbol>""",
    "caspase": """<symbol id="caspase" viewBox="0 0 72 52" overflow="visible">
        <!-- Caspase heterodimer: large subunit + small subunit, with a
             visible active-site cleft. Purple palette to distinguish from
             MMP (coral). Caspases are cysteine proteases that cleave at
             Asp residues — execution / initiator caspase. -->
        <ellipse cx="26" cy="26" rx="22" ry="18"
              fill="#C5A8E2" stroke="#5F3A8C" stroke-width="2"/>
        <ellipse cx="58" cy="26" rx="13" ry="11"
              fill="#D8BCE8" stroke="#5F3A8C" stroke-width="2"/>
        <!-- Active-site cleft (dashed arc between subunits) -->
        <path d="M 42 14 Q 47 26 42 38" fill="none"
              stroke="#3F2A5C" stroke-width="1.6" stroke-linecap="round"
              stroke-dasharray="3,2"/>
        <!-- Cys label inside large subunit (catalytic cysteine) -->
        <text x="26" y="30" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif" font-size="9"
              fill="#3F2A5C" font-weight="bold">Cys</text>
    </symbol>""",
}

_SIGNALING_EXTENDED: dict[str, str] = {
    # Hand-written signaling-pathway extensions. bioicons.com has no
    # named-protein icons for signaling (only generic membrane shapes which
    # we already cover via gpcr/rtk/kinase). These fill specific gaps that
    # came up while drafting pathway figures.
    "transcription_factor": """<symbol id="transcription_factor" viewBox="0 0 60 50" overflow="visible">
        <!-- Saddle / arch body -->
        <path d="M 10 30 Q 10 6 30 6 Q 50 6 50 30 Z"
              fill="#B5D4A8" stroke="#4A7A3F" stroke-width="2" stroke-linejoin="round"/>
        <!-- DNA-binding fingers / contact points -->
        <line x1="17" y1="30" x2="17" y2="42" stroke="#4A7A3F" stroke-width="2.5" stroke-linecap="round"/>
        <line x1="43" y1="30" x2="43" y2="42" stroke="#4A7A3F" stroke-width="2.5" stroke-linecap="round"/>
        <!-- DNA double helix beneath (suggested with two parallel waves) -->
        <path d="M 2 45 Q 12 41 22 45 T 42 45 Q 52 41 58 45"
              fill="none" stroke="#888888" stroke-width="1.5"/>
        <path d="M 2 48 Q 12 52 22 48 T 42 48 Q 52 52 58 48"
              fill="none" stroke="#888888" stroke-width="1.5"/>
    </symbol>""",
    "scaffold_protein": """<symbol id="scaffold_protein" viewBox="0 0 130 32" overflow="visible">
        <!-- Outer rectangle = scaffold backbone -->
        <rect x="2" y="2" width="126" height="28" rx="6"
              fill="#EAEAEA" stroke="#666666" stroke-width="1.5"/>
        <!-- 4 colored sub-domains showing distinct binding regions -->
        <rect x="6" y="6" width="24" height="20" rx="3"
              fill="#B5D4A8" stroke="#4A7A3F" stroke-width="1.2"/>
        <rect x="34" y="6" width="24" height="20" rx="3"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1.2"/>
        <rect x="62" y="6" width="24" height="20" rx="3"
              fill="#FFD4B0" stroke="#C86B1F" stroke-width="1.2"/>
        <rect x="90" y="6" width="34" height="20" rx="3"
              fill="#D4B8E2" stroke="#7F4A9C" stroke-width="1.2"/>
    </symbol>""",
    "small_gtpase": """<symbol id="small_gtpase" viewBox="0 0 52 48" overflow="visible">
        <!-- Body: rounded triangle (Ras-family GTPase typical depiction) -->
        <path d="M 26 4 L 46 36 Q 26 46 6 36 Z"
              fill="#C5B5D4" stroke="#5F4A7F" stroke-width="2" stroke-linejoin="round"/>
        <!-- Bound nucleotide (GTP active or GDP inactive — label via text) -->
        <circle cx="36" cy="24" r="7"
              fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <text x="36" y="27" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif"
              font-size="8" fill="#C8901F" font-weight="bold">T</text>
    </symbol>""",
    "ligand": """<symbol id="ligand" viewBox="0 0 40 30" overflow="visible">
        <!-- Generic growth factor / cytokine: small clover-shaped blob -->
        <path d="M 20 5 Q 8 5 8 15 Q 8 25 20 25 Q 32 25 32 15 Q 32 5 20 5 Z"
              fill="#FFD8B0" stroke="#C86B1F" stroke-width="1.8"
              stroke-linejoin="round"/>
        <!-- Two small lobes for visual texture -->
        <circle cx="14" cy="13" r="3" fill="#FFC890" stroke="#C86B1F" stroke-width="1.2"/>
        <circle cx="26" cy="17" r="3" fill="#FFC890" stroke="#C86B1F" stroke-width="1.2"/>
    </symbol>""",
    "g_protein_trimer": """<symbol id="g_protein_trimer" viewBox="0 0 90 60" overflow="visible">
        <!-- Gα subunit (largest, with GDP/GTP slot) -->
        <ellipse cx="28" cy="32" rx="22" ry="18"
              fill="#A8C5D4" stroke="#3A5F7F" stroke-width="2"/>
        <text x="28" y="36" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif" font-size="12"
              fill="#3A5F7F" font-weight="bold">α</text>
        <!-- Gβ subunit (medium) -->
        <ellipse cx="62" cy="22" rx="16" ry="14"
              fill="#B5D4A8" stroke="#4A7A3F" stroke-width="2"/>
        <text x="62" y="26" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif" font-size="11"
              fill="#4A7A3F" font-weight="bold">β</text>
        <!-- Gγ subunit (smallest) -->
        <ellipse cx="74" cy="44" rx="12" ry="10"
              fill="#D4B8E2" stroke="#7F4A9C" stroke-width="2"/>
        <text x="74" y="48" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif" font-size="10"
              fill="#7F4A9C" font-weight="bold">γ</text>
    </symbol>""",
}

_SMALL_MOLECULES: dict[str, str] = {
    "ion": """<symbol id="ion" viewBox="0 0 30 30" overflow="visible">
        <circle cx="15" cy="15" r="13"
              fill="#D4B8E2" stroke="#7F4A9C" stroke-width="1.5"/>
    </symbol>""",
    "atp": """<symbol id="atp" viewBox="0 0 80 30" overflow="visible">
        <polygon points="5,15 13,5 25,5 33,15 25,25 13,25"
              fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="48" cy="15" r="6" fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="60" cy="15" r="6" fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="72" cy="15" r="6" fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="33" y1="15" x2="42" y2="15" stroke="#C8901F" stroke-width="1.5"/>
    </symbol>""",
    "adp": """<symbol id="adp" viewBox="0 0 70 30" overflow="visible">
        <polygon points="5,15 13,5 25,5 33,15 25,25 13,25"
              fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="48" cy="15" r="6" fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="60" cy="15" r="6" fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="33" y1="15" x2="42" y2="15" stroke="#C8901F" stroke-width="1.5"/>
    </symbol>""",
    "camp": """<symbol id="camp" viewBox="0 0 50 32" overflow="visible">
        <polygon points="5,18 12,8 24,8 31,18 24,28 12,28"
              fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="40" cy="18" r="6" fill="#FFE8B0" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="31" y1="18" x2="34" y2="18" stroke="#C8901F" stroke-width="1.5"/>
        <path d="M 18 8 Q 18 2 25 2 Q 32 2 32 8" fill="none" stroke="#C8901F" stroke-width="1.5"/>
    </symbol>""",
    "ip3": """<symbol id="ip3" viewBox="0 0 40 40" overflow="visible">
        <circle cx="20" cy="20" r="14"
              fill="#E8C5D4" stroke="#9C4A6F" stroke-width="1.5"/>
        <circle cx="10" cy="10" r="3" fill="#9C4A6F"/>
        <circle cx="30" cy="10" r="3" fill="#9C4A6F"/>
        <circle cx="20" cy="33" r="3" fill="#9C4A6F"/>
    </symbol>""",
    "dag": """<symbol id="dag" viewBox="0 0 50 40" overflow="visible">
        <rect x="5" y="15" width="13" height="10" rx="2"
              fill="#FFD4B0" stroke="#C86B1F" stroke-width="1.5"/>
        <path d="M 18 18 L 26 12 L 34 18 L 42 12"
              fill="none" stroke="#C86B1F" stroke-width="1.5"/>
        <path d="M 18 22 L 26 28 L 34 22 L 42 28"
              fill="none" stroke="#C86B1F" stroke-width="1.5"/>
    </symbol>""",
}

_MODIFICATIONS: dict[str, str] = {
    "p_badge": """<symbol id="p_badge" viewBox="0 0 24 24" overflow="visible">
        <circle cx="12" cy="12" r="10"
              fill="#FF6B47" stroke="#A33020" stroke-width="1.5"/>
        <text x="12" y="16" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif"
              font-size="12" fill="white" font-weight="bold">P</text>
    </symbol>""",
    "ub_badge": """<symbol id="ub_badge" viewBox="0 0 28 24" overflow="visible">
        <circle cx="14" cy="12" r="10"
              fill="#9C4ACC" stroke="#5A2A7C" stroke-width="1.5"/>
        <text x="14" y="16" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif"
              font-size="9" fill="white" font-weight="bold">Ub</text>
    </symbol>""",
    "ac_badge": """<symbol id="ac_badge" viewBox="0 0 28 24" overflow="visible">
        <circle cx="14" cy="12" r="10"
              fill="#5AB85A" stroke="#2A722A" stroke-width="1.5"/>
        <text x="14" y="16" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif"
              font-size="9" fill="white" font-weight="bold">Ac</text>
    </symbol>""",
}

_ORGANELLES: dict[str, str] = {
    "nucleus": """<symbol id="nucleus" viewBox="0 0 200 150" overflow="visible">
        <ellipse cx="100" cy="75" rx="92" ry="65"
              fill="#F0E0F0" stroke="#5A2A7C" stroke-width="2.5"/>
        <ellipse cx="100" cy="75" rx="86" ry="60"
              fill="none" stroke="#5A2A7C" stroke-width="1" opacity="0.6"/>
        <circle cx="20" cy="60" r="3" fill="#5A2A7C"/>
        <circle cx="180" cy="65" r="3" fill="#5A2A7C"/>
        <circle cx="100" cy="12" r="3" fill="#5A2A7C"/>
        <circle cx="100" cy="138" r="3" fill="#5A2A7C"/>
    </symbol>""",
    "mitochondrion": """<symbol id="mitochondrion" viewBox="0 0 150 80" overflow="visible">
        <ellipse cx="75" cy="40" rx="70" ry="35"
              fill="#F5D4C5" stroke="#8B4A2A" stroke-width="2.5"/>
        <path d="M 30 26 Q 40 36 50 26 Q 60 16 70 26"
              fill="none" stroke="#8B4A2A" stroke-width="1.5"/>
        <path d="M 30 54 Q 40 44 50 54 Q 60 64 70 54"
              fill="none" stroke="#8B4A2A" stroke-width="1.5"/>
        <path d="M 80 26 Q 90 36 100 26 Q 110 16 120 26"
              fill="none" stroke="#8B4A2A" stroke-width="1.5"/>
        <path d="M 80 54 Q 90 44 100 54 Q 110 64 120 54"
              fill="none" stroke="#8B4A2A" stroke-width="1.5"/>
    </symbol>""",
    "er_compartment": """<symbol id="er_compartment" viewBox="0 0 200 120" overflow="visible">
        <path d="M 10 30 Q 50 12 90 30 T 190 30 L 190 90 Q 150 108 110 90 T 10 90 Z"
              fill="#F5E8D0" stroke="#8B6F35" stroke-width="2"/>
    </symbol>""",
    "golgi": """<symbol id="golgi" viewBox="0 0 120 80" overflow="visible">
        <path d="M 10 20 Q 60 10 110 20" stroke="#8B4A8B" stroke-width="2.5" fill="none"/>
        <path d="M 12 32 Q 60 24 108 32" stroke="#8B4A8B" stroke-width="2.5" fill="none"/>
        <path d="M 14 44 Q 60 38 106 44" stroke="#8B4A8B" stroke-width="2.5" fill="none"/>
        <path d="M 16 56 Q 60 52 104 56" stroke="#8B4A8B" stroke-width="2.5" fill="none"/>
        <path d="M 18 68 Q 60 66 102 68" stroke="#8B4A8B" stroke-width="2.5" fill="none"/>
    </symbol>""",
    "autophagosome": """<symbol id="autophagosome" viewBox="0 0 80 80" overflow="visible">
        <!-- Outer membrane -->
        <circle cx="40" cy="40" r="36"
              fill="#E8F0F2" stroke="#5F7F8C" stroke-width="2"/>
        <!-- Inner membrane (the defining feature — autophagosomes are DOUBLE-membraned) -->
        <circle cx="40" cy="40" r="30"
              fill="#FAFAFA" stroke="#5F7F8C" stroke-width="2"/>
        <!-- Cargo: a damaged mitochondrion fragment being engulfed -->
        <ellipse cx="40" cy="40" rx="20" ry="11"
              fill="#F5D4C5" stroke="#8B4A2A" stroke-width="1.5"/>
        <path d="M 28 40 Q 34 36 40 40 Q 46 44 52 40"
              fill="none" stroke="#8B4A2A" stroke-width="1.2"/>
    </symbol>""",
    "lysosome": """<symbol id="lysosome" viewBox="0 0 60 60" overflow="visible">
        <!-- Single membrane with acidic interior (purple palette signals
             low pH / digestive function). -->
        <circle cx="30" cy="30" r="26"
              fill="#E2C5D8" stroke="#7F4A6F" stroke-width="2"/>
        <!-- Hydrolase enzymes scattered inside -->
        <circle cx="22" cy="22" r="2.5" fill="#7F4A6F"/>
        <circle cx="38" cy="20" r="2.5" fill="#7F4A6F"/>
        <circle cx="42" cy="35" r="2.5" fill="#7F4A6F"/>
        <circle cx="22" cy="40" r="2.5" fill="#7F4A6F"/>
        <circle cx="33" cy="44" r="2.5" fill="#7F4A6F"/>
        <circle cx="30" cy="30" r="2.5" fill="#7F4A6F"/>
    </symbol>""",
}

_ECM_EXTENDED: dict[str, str] = {
    # Hand-written matrix-protein extensions beyond the bundled
    # bioicons_collagen. bioicons.com doesn't carry named fibronectin /
    # laminin / proteoglycan icons. Style: peach/coral palette
    # (matches the broader matrix aesthetic without colliding with the
    # green of cytosolic enzymes or the blue of membrane receptors).
    "fibronectin": """<symbol id="fibronectin" viewBox="0 0 180 70" overflow="visible">
        <!-- V-shaped dimer with binding-domain beads along each arm.
             Each arm is a thin tube of repeating FN domains. -->
        <!-- Arm 1: top-left to bottom-centre -->
        <line x1="8" y1="8" x2="90" y2="50" stroke="#C86B47" stroke-width="3" stroke-linecap="round"/>
        <!-- Arm 2: top-right to bottom-centre (joins at the same point) -->
        <line x1="172" y1="8" x2="90" y2="50" stroke="#C86B47" stroke-width="3" stroke-linecap="round"/>
        <!-- Domain beads along each arm -->
        <circle cx="20"  cy="14" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="38"  cy="23" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="56"  cy="32" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="74"  cy="41" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="160" cy="14" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="142" cy="23" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="124" cy="32" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="106" cy="41" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <!-- Junction node where arms meet -->
        <circle cx="90"  cy="50" r="6" fill="#FFC890" stroke="#C86B47" stroke-width="1.8"/>
        <!-- RGD binding loop at junction (the integrin-binding motif) -->
        <path d="M 86 56 Q 90 64 94 56" fill="none" stroke="#C86B47" stroke-width="1.8" stroke-linecap="round"/>
    </symbol>""",
    "laminin": """<symbol id="laminin" viewBox="0 0 120 120" overflow="visible">
        <!-- Cross-shaped molecule: 3 short arms + 1 long arm. Each arm
             is a chain of small globular domains; the centre is a hub. -->
        <!-- Long arm pointing down (cell-binding region) -->
        <line x1="60" y1="60" x2="60" y2="112" stroke="#C86B47" stroke-width="3" stroke-linecap="round"/>
        <circle cx="60" cy="72" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="60" cy="86" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="60" cy="100" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="60" cy="112" r="7" fill="#FFC890" stroke="#C86B47" stroke-width="1.8"/>
        <!-- Short arms: up, left, right -->
        <line x1="60" y1="60" x2="60" y2="14" stroke="#C86B47" stroke-width="3" stroke-linecap="round"/>
        <circle cx="60" cy="32" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="60" cy="14" r="6" fill="#FFC890" stroke="#C86B47" stroke-width="1.8"/>

        <line x1="60" y1="60" x2="12" y2="60" stroke="#C86B47" stroke-width="3" stroke-linecap="round"/>
        <circle cx="36" cy="60" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="12" cy="60" r="6" fill="#FFC890" stroke="#C86B47" stroke-width="1.8"/>

        <line x1="60" y1="60" x2="108" y2="60" stroke="#C86B47" stroke-width="3" stroke-linecap="round"/>
        <circle cx="84"  cy="60" r="4" fill="#FFD4B0" stroke="#C86B47" stroke-width="1.2"/>
        <circle cx="108" cy="60" r="6" fill="#FFC890" stroke="#C86B47" stroke-width="1.8"/>
        <!-- Centre hub -->
        <circle cx="60" cy="60" r="8" fill="#FFB870" stroke="#C86B47" stroke-width="2"/>
    </symbol>""",
    "basement_membrane": """<symbol id="basement_membrane" viewBox="0 0 200 28" overflow="visible" preserveAspectRatio="xMidYMid meet">
        <!-- Two-layer structure: lamina lucida (top, lighter) + lamina
             densa (bottom, darker). The matrix-protein palette (peach/coral)
             matches collagen/fibronectin/laminin for visual coherence. -->
        <rect x="0" y="2"  width="200" height="11"
              fill="#FFE0C8" stroke="#C86B47" stroke-width="1"/>
        <rect x="0" y="14" width="200" height="11"
              fill="#FFF0E0" stroke="#C86B47" stroke-width="1"/>
        <!-- Faint lattice ticks to suggest collagen IV network -->
        <line x1="20"  y1="2" x2="20"  y2="25" stroke="#C86B47" stroke-width="0.5" opacity="0.4"/>
        <line x1="60"  y1="2" x2="60"  y2="25" stroke="#C86B47" stroke-width="0.5" opacity="0.4"/>
        <line x1="100" y1="2" x2="100" y2="25" stroke="#C86B47" stroke-width="0.5" opacity="0.4"/>
        <line x1="140" y1="2" x2="140" y2="25" stroke="#C86B47" stroke-width="0.5" opacity="0.4"/>
        <line x1="180" y1="2" x2="180" y2="25" stroke="#C86B47" stroke-width="0.5" opacity="0.4"/>
    </symbol>""",
    "hemidesmosome": """<symbol id="hemidesmosome" viewBox="0 0 100 92" overflow="visible">
        <!-- Cell side (top): cytoplasmic plaque + intermediate filaments -->
        <line x1="20" y1="3"  x2="20" y2="20" stroke="#888888" stroke-width="1.5"/>
        <line x1="35" y1="3"  x2="35" y2="20" stroke="#888888" stroke-width="1.5"/>
        <line x1="50" y1="3"  x2="50" y2="20" stroke="#888888" stroke-width="1.5"/>
        <line x1="65" y1="3"  x2="65" y2="20" stroke="#888888" stroke-width="1.5"/>
        <line x1="80" y1="3"  x2="80" y2="20" stroke="#888888" stroke-width="1.5"/>
        <rect x="14" y="20" width="72" height="7" rx="1.5"
              fill="#E8E8E8" stroke="#555555" stroke-width="1.5"/>
        <!-- Cell membrane (2 lines) -->
        <line x1="0" y1="33" x2="100" y2="33" stroke="#888888" stroke-width="1.5"/>
        <line x1="0" y1="39" x2="100" y2="39" stroke="#888888" stroke-width="1.5"/>
        <!-- α6β4 integrin anchors crossing the membrane (4 transmembrane bars) -->
        <rect x="20" y="27" width="6" height="22" rx="1.5"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1.3"/>
        <rect x="38" y="27" width="6" height="22" rx="1.5"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1.3"/>
        <rect x="56" y="27" width="6" height="22" rx="1.5"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1.3"/>
        <rect x="74" y="27" width="6" height="22" rx="1.5"
              fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1.3"/>
        <!-- Basement membrane below -->
        <rect x="0" y="56" width="100" height="20"
              fill="#FFE0C8" stroke="#C86B47" stroke-width="1.5"/>
        <rect x="0" y="76" width="100" height="14"
              fill="#FFF0E0" stroke="#C86B47" stroke-width="1.2"/>
        <text x="50" y="69" text-anchor="middle"
              font-family="Helvetica, Arial, sans-serif" font-size="8"
              fill="#9C4A47">BM</text>
    </symbol>""",
    "proteoglycan": """<symbol id="proteoglycan" viewBox="0 0 200 90" overflow="visible">
        <!-- Bottle-brush: long core protein with many GAG side-chains.
             Core protein: horizontal line. Side chains: vertical "bristles". -->
        <!-- Core protein (gelsolin-like backbone) -->
        <line x1="8" y1="45" x2="192" y2="45" stroke="#9C4A6F" stroke-width="4" stroke-linecap="round"/>
        <!-- Linking proteins / small globular domains along core -->
        <circle cx="20"  cy="45" r="3" fill="#D4A8C5" stroke="#9C4A6F" stroke-width="1"/>
        <circle cx="180" cy="45" r="3" fill="#D4A8C5" stroke="#9C4A6F" stroke-width="1"/>
        <!-- GAG bristles (top side) — chains of small beads -->""" + "\n".join(
        f'        <line x1="{x}" y1="40" x2="{x}" y2="10" stroke="#C86B9C" stroke-width="1.5" stroke-linecap="round"/>\n'
        f'        <circle cx="{x}" cy="18" r="2" fill="#E8B8D4" stroke="#9C4A6F" stroke-width="0.8"/>\n'
        f'        <circle cx="{x}" cy="26" r="2" fill="#E8B8D4" stroke="#9C4A6F" stroke-width="0.8"/>\n'
        f'        <circle cx="{x}" cy="34" r="2" fill="#E8B8D4" stroke="#9C4A6F" stroke-width="0.8"/>'
        for x in range(30, 175, 16)
    ) + """
        <!-- GAG bristles (bottom side) -->""" + "\n".join(
        f'        <line x1="{x}" y1="50" x2="{x}" y2="80" stroke="#C86B9C" stroke-width="1.5" stroke-linecap="round"/>\n'
        f'        <circle cx="{x}" cy="58" r="2" fill="#E8B8D4" stroke="#9C4A6F" stroke-width="0.8"/>\n'
        f'        <circle cx="{x}" cy="66" r="2" fill="#E8B8D4" stroke="#9C4A6F" stroke-width="0.8"/>\n'
        f'        <circle cx="{x}" cy="74" r="2" fill="#E8B8D4" stroke="#9C4A6F" stroke-width="0.8"/>'
        for x in range(38, 175, 16)
    ) + """
    </symbol>""",
}


_STRUCTURAL: dict[str, str] = {
    "lipid_bilayer": """<symbol id="lipid_bilayer" viewBox="0 0 100 24" overflow="visible" preserveAspectRatio="xMidYMid meet">
        <circle cx="10" cy="6" r="4" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="25" cy="6" r="4" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="40" cy="6" r="4" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="55" cy="6" r="4" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="70" cy="6" r="4" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="85" cy="6" r="4" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <line x1="10" y1="10" x2="10" y2="16" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="25" y1="10" x2="25" y2="16" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="40" y1="10" x2="40" y2="16" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="55" y1="10" x2="55" y2="16" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="70" y1="10" x2="70" y2="16" stroke="#C8901F" stroke-width="1.5"/>
        <line x1="85" y1="10" x2="85" y2="16" stroke="#C8901F" stroke-width="1.5"/>
        <circle cx="10" cy="20" r="3" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="25" cy="20" r="3" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="40" cy="20" r="3" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="55" cy="20" r="3" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="70" cy="20" r="3" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
        <circle cx="85" cy="20" r="3" fill="#FFE8B0" stroke="#C8901F" stroke-width="1"/>
    </symbol>""",
}


_GENERAL: dict[str, str] = {
    "microscope": """<symbol id="microscope" viewBox="0 0 40 60" overflow="visible">
        <rect x="6" y="50" width="28" height="6" rx="2" fill="#5A6B7F" stroke="#2A3F55" stroke-width="1.5"/>
        <rect x="16" y="22" width="8" height="30" fill="#5A6B7F" stroke="#2A3F55" stroke-width="1.5"/>
        <rect x="10" y="42" width="20" height="3" fill="#2A3F55"/>
        <rect x="17" y="36" width="6" height="6" fill="#A8C5E2" stroke="#2A3F55" stroke-width="1.5"/>
        <line x1="20" y1="22" x2="14" y2="10" stroke="#2A3F55" stroke-width="3" stroke-linecap="round"/>
        <circle cx="14" cy="10" r="3.5" fill="#A8C5E2" stroke="#2A3F55" stroke-width="1.5"/>
    </symbol>""",
    "lab_flask": """<symbol id="lab_flask" viewBox="0 0 40 50" overflow="visible">
        <rect x="17" y="5" width="6" height="10" fill="#E5E5E5" stroke="#4A7A3F" stroke-width="1.5"/>
        <path d="M 17 15 L 6 42 Q 20 50 34 42 L 23 15 Z"
              fill="#B5D4A8" stroke="#4A7A3F" stroke-width="1.5"/>
        <line x1="11" y1="35" x2="29" y2="35" stroke="#4A7A3F" stroke-width="1" stroke-dasharray="2,2"/>
        <circle cx="14" cy="40" r="1.5" fill="#4A7A3F" opacity="0.5"/>
        <circle cx="22" cy="38" r="1.2" fill="#4A7A3F" opacity="0.5"/>
    </symbol>""",
    "pill_capsule": """<symbol id="pill_capsule" viewBox="0 0 60 25" overflow="visible">
        <path d="M 30 5 L 11 5 Q 3 5 3 12.5 Q 3 20 11 20 L 30 20 Z"
              fill="#FFE0B0" stroke="#9C5F2A" stroke-width="1.5"/>
        <path d="M 30 5 L 49 5 Q 57 5 57 12.5 Q 57 20 49 20 L 30 20 Z"
              fill="#FFB570" stroke="#9C5F2A" stroke-width="1.5"/>
    </symbol>""",
    "patient_silhouette": """<symbol id="patient_silhouette" viewBox="0 0 40 55" overflow="visible">
        <circle cx="20" cy="14" r="9" fill="#E8C5B5" stroke="#9C5F47" stroke-width="1.5"/>
        <path d="M 5 50 L 8 32 Q 12 25 20 25 Q 28 25 32 32 L 35 50 Z"
              fill="#E8C5B5" stroke="#9C5F47" stroke-width="1.5"/>
    </symbol>""",
    "document_stamp": """<symbol id="document_stamp" viewBox="0 0 45 50" overflow="visible">
        <path d="M 5 5 L 32 5 L 40 13 L 40 45 L 5 45 Z"
              fill="#FFFFFF" stroke="#444444" stroke-width="1.5"/>
        <path d="M 32 5 L 32 13 L 40 13 Z" fill="#DDDDDD" stroke="#444444" stroke-width="1.5"/>
        <line x1="10" y1="20" x2="35" y2="20" stroke="#888888" stroke-width="1"/>
        <line x1="10" y1="25" x2="35" y2="25" stroke="#888888" stroke-width="1"/>
        <line x1="10" y1="30" x2="30" y2="30" stroke="#888888" stroke-width="1"/>
        <circle cx="32" cy="38" r="7" fill="none" stroke="#D03020" stroke-width="2"/>
        <path d="M 28 38 L 31 41 L 36 35" fill="none" stroke="#D03020" stroke-width="2" stroke-linecap="round"/>
    </symbol>""",
    "chart_graph": """<symbol id="chart_graph" viewBox="0 0 50 40" overflow="visible">
        <line x1="6" y1="5" x2="6" y2="35" stroke="#444444" stroke-width="1.5"/>
        <line x1="6" y1="35" x2="46" y2="35" stroke="#444444" stroke-width="1.5"/>
        <rect x="10" y="25" width="6" height="10" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1"/>
        <rect x="20" y="18" width="6" height="17" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1"/>
        <rect x="30" y="12" width="6" height="23" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1"/>
        <rect x="40" y="8" width="6" height="27" fill="#A8C5E2" stroke="#3A5F7F" stroke-width="1"/>
        <path d="M 13 23 L 23 16 L 33 10 L 43 6" fill="none" stroke="#D03020" stroke-width="1.5"/>
    </symbol>""",
    "milestone_marker": """<symbol id="milestone_marker" viewBox="0 0 30 40" overflow="visible">
        <line x1="6" y1="5" x2="6" y2="38" stroke="#444444" stroke-width="2"/>
        <ellipse cx="6" cy="38" rx="4" ry="1.5" fill="#444444"/>
        <path d="M 6 6 L 26 11 L 6 16 Z" fill="#FF8847" stroke="#9C4A20" stroke-width="1.5"/>
    </symbol>""",
    "gear": """<symbol id="gear" viewBox="0 0 40 40" overflow="visible">
        <g fill="#D4D4D4" stroke="#666666" stroke-width="1.5">
            <rect x="18" y="2" width="4" height="6"/>
            <rect x="18" y="32" width="4" height="6"/>
            <rect x="2" y="18" width="6" height="4"/>
            <rect x="32" y="18" width="6" height="4"/>
        </g>
        <circle cx="20" cy="20" r="11" fill="#D4D4D4" stroke="#666666" stroke-width="1.5"/>
        <circle cx="20" cy="20" r="4" fill="#FFFFFF" stroke="#666666" stroke-width="1.5"/>
    </symbol>""",
    "clock": """<symbol id="clock" viewBox="0 0 40 40" overflow="visible">
        <circle cx="20" cy="20" r="17" fill="#F5F5F5" stroke="#444444" stroke-width="2"/>
        <line x1="20" y1="5" x2="20" y2="9" stroke="#444444" stroke-width="1.5"/>
        <line x1="35" y1="20" x2="31" y2="20" stroke="#444444" stroke-width="1.5"/>
        <line x1="20" y1="35" x2="20" y2="31" stroke="#444444" stroke-width="1.5"/>
        <line x1="5" y1="20" x2="9" y2="20" stroke="#444444" stroke-width="1.5"/>
        <line x1="20" y1="20" x2="20" y2="11" stroke="#222222" stroke-width="2" stroke-linecap="round"/>
        <line x1="20" y1="20" x2="27" y2="20" stroke="#222222" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="20" cy="20" r="1.5" fill="#222222"/>
    </symbol>""",
    "magnifying_glass": """<symbol id="magnifying_glass" viewBox="0 0 40 40" overflow="visible">
        <circle cx="16" cy="16" r="11" fill="#FFFFFF" stroke="#3A5F7F" stroke-width="2.5"/>
        <circle cx="16" cy="16" r="9" fill="#A8C5E2" opacity="0.3"/>
        <line x1="24" y1="24" x2="36" y2="36" stroke="#3A5F7F" stroke-width="3" stroke-linecap="round"/>
    </symbol>""",
}


SYMBOLS: dict[str, str] = {
    **_RECEPTORS,
    **_ENZYMES,
    **_SIGNALING_EXTENDED,
    **_SMALL_MOLECULES,
    **_MODIFICATIONS,
    **_ORGANELLES,
    **_ECM_EXTENDED,
    **_STRUCTURAL,
    **_GENERAL,
    # Third-party detail-rich icons (bundled, see ATTRIBUTIONS.md).
    **BIOICONS,
    # Per-stage sub-region wrappers (thin viewBox-crops of BIOICONS composites).
    **BIOICONS_SUBREGIONS,
}


CATALOG: list[SymbolEntry] = [
    # Receptors / membrane proteins
    SymbolEntry("gpcr", "GPCR", "receptor",
                "G-protein-coupled / 7-transmembrane receptors. Examples: AT1R, β-adrenergic, rhodopsin.",
                60, 80),
    SymbolEntry("rtk", "RTK", "receptor",
                "Receptor tyrosine kinases with extracellular ligand-binding + intracellular kinase domain. Examples: EGFR, insulin receptor.",
                60, 100),
    SymbolEntry("ion_channel", "Ion channel", "receptor",
                "Membrane ion channels (voltage-gated, ligand-gated, leak). Pore visible between two subunits.",
                60, 80),
    SymbolEntry("transporter", "Transporter", "receptor",
                "Active or facilitated transporters. Arrow inside indicates direction.",
                60, 80),
    SymbolEntry("generic_membrane_protein", "Generic membrane protein", "receptor",
                "Membrane protein that doesn't fit a more specific category.",
                60, 80),
    SymbolEntry("mhc_complex", "MHC class I/II (antigen-presenting)",
                "receptor",
                "Antigen-presenting molecule: transmembrane body with an "
                "open peptide-binding groove on top holding a small magenta "
                "peptide. Use for antigen-presentation figures (MHC-I on "
                "all nucleated cells, MHC-II on APCs). Place on the antigen-"
                "presenting cell's surface; the peptide groove faces a TCR "
                "on a facing T-lymphocyte. Add a <text> for the specific "
                "isoform (MHC-I, MHC-II, HLA-A2, etc.).",
                50, 80),
    SymbolEntry("integrin", "Integrin (αβ heterodimer)", "receptor",
                "Cell-matrix adhesion receptor — heterodimer of α and β "
                "subunits (labels live inside each body). Extracellular heads "
                "bind ECM components (collagen, fibronectin, laminin); "
                "cytoplasmic tails connect to actin via talin/vinculin. Place "
                "straddling the membrane with the α/β heads above and short "
                "cytoplasmic tails below. The natural bridge between cells "
                "and the ECM.",
                60, 92),
    SymbolEntry("cadherin", "Cadherin (cell-cell adhesion)", "receptor",
                "Cell-cell adhesion receptor — single transmembrane chain "
                "with 5 extracellular cadherin (EC) domains stacked vertically. "
                "Pair two cadherins on facing membranes (mirror-image, EC1 "
                "to EC1) to depict adherens junctions between cells. "
                "Cytoplasmic tail connects to β-catenin and actin. Distinct "
                "from integrin (which binds ECM, not other cells).",
                32, 96),
    # Cytosolic enzymes
    SymbolEntry("kinase", "Kinase", "enzyme",
                "Cytosolic kinase enzymes. Examples: PKA, PKC, MAPK, Akt.",
                80, 50),
    SymbolEntry("phosphatase", "Phosphatase", "enzyme",
                "Cytosolic phosphatases. Examples: PP2A, PTP.",
                80, 50),
    SymbolEntry("generic_protein", "Generic protein", "enzyme",
                "Cytosolic protein that doesn't fit a more specific category.",
                80, 50),
    SymbolEntry("complex", "Protein complex", "enzyme",
                "Multi-subunit cytosolic complex. Examples: G-protein heterotrimer, RISC, ribosome.",
                110, 60),
    SymbolEntry("caspase", "Caspase (apoptosis protease)", "enzyme",
                "Heterodimer with large + small subunit and a dashed "
                "active-site cleft, purple palette to distinguish from MMP. "
                "Use in apoptosis cascade figures: initiator caspases "
                "(caspase-8/9) → executioner caspases (caspase-3/7) → "
                "substrate cleavage (DNA fragmentation, PARP, lamins). Add "
                "a <text> label above for the specific caspase number.",
                72, 52),
    SymbolEntry("mmp", "Matrix metalloproteinase (MMP)", "enzyme",
                "Pac-Man shape (open mouth facing right) with a yellow Zn²⁺ "
                "cofactor at the active site, coral colour to signal "
                "matrix-cleaving function. Use for matrix remodelling, "
                "wound healing, tumour invasion, basement-membrane "
                "degradation. Place near or adjacent to a collagen / "
                "fibronectin fibre being cleaved; draw a discontinuity in "
                "the substrate at the MMP mouth to show the cut.",
                50, 50),
    # Signaling-pathway extensions — hand-written for specific roles that
    # the generic enzyme/protein shapes cannot convey.
    SymbolEntry("transcription_factor", "Transcription factor", "signaling",
                "DNA-binding regulatory protein. Saddle/arch shape with two "
                "DNA-contact 'fingers' descending onto a double-helix line. "
                "Place near a target gene; the double helix is drawn as part "
                "of the symbol but you can overlay your own DNA labels.",
                60, 50),
    SymbolEntry("scaffold_protein", "Scaffold / multi-domain protein", "signaling",
                "Elongated multi-domain backbone with 4 coloured sub-domains. "
                "Use for scaffold/adaptor proteins (e.g. KSR, JIP, Ste5) that "
                "tether multiple signalling partners. Each coloured sub-domain "
                "is a generic 'binding pocket' — the LLM should NOT label them "
                "individually unless the figure context warrants it.",
                130, 32),
    SymbolEntry("small_gtpase", "Small GTPase (Ras-family)", "signaling",
                "Triangular protein with a bound nucleotide (T-marked circle "
                "indicates GTP — the active state). Use for Ras, RhoA, Rac1, "
                "Cdc42, Rab, Ran. Add a <text> label above for the specific "
                "GTPase. For the inactive form, the LLM can override the inner "
                "'T' text to 'D' via additional <text> overlay.",
                52, 48),
    SymbolEntry("ligand", "Ligand (any signalling molecule)", "signaling",
                "Generic small ligand — clover-shaped peach blob. Use for ANY "
                "signalling molecule that binds a receptor or is internalised "
                "to act inside the cell: peptide growth factors (EGF, FGF, "
                "VEGF, TGF-β, insulin), cytokines, neurotransmitters, AND "
                "lipophilic hormones / steroid hormones (cortisol, oestrogen, "
                "testosterone, thyroid hormone). For surface-receptor pathways "
                "place above a receptor (gpcr / rtk / integrin); for nuclear-"
                "receptor pathways place it inside the cytoplasm next to a "
                "cytoplasmic receptor (use `generic_protein` for the unbound "
                "receptor, `transcription_factor` for the hormone-receptor "
                "complex on DNA). Label the specific ligand with a `<text>` "
                "next to the icon.",
                40, 30),
    SymbolEntry("g_protein_trimer", "G-protein heterotrimer (αβγ)", "signaling",
                "G-protein heterotrimer with three distinguishable subunits — "
                "Gα (blue, with α label), Gβ (green, β label), Gγ (purple, "
                "γ label). Place INSIDE the cytoplasm directly below a GPCR. "
                "Distinct from the generic `complex` symbol; use this whenever "
                "G-protein signalling is specifically depicted.",
                90, 60),
    # Small molecules / ions
    SymbolEntry("ion", "Ion / charge carrier", "small_molecule",
                "Generic small ion or charged molecule. Add an adjacent <text> for the species (Ca²⁺, Na⁺, K⁺, H⁺, Cl⁻, Mg²⁺).",
                30, 30),
    SymbolEntry("atp", "ATP", "small_molecule",
                "Adenosine triphosphate. Hexagon (adenosine) + 3 circles (phosphates).",
                80, 30),
    SymbolEntry("adp", "ADP", "small_molecule",
                "Adenosine diphosphate. Hexagon + 2 circles.",
                70, 30),
    SymbolEntry("camp", "cAMP", "small_molecule",
                "Cyclic AMP. Hexagon with cyclic notation + 1 phosphate.",
                50, 32),
    SymbolEntry("ip3", "IP₃", "small_molecule",
                "Inositol 1,4,5-trisphosphate. Circle with 3 phosphate marks.",
                40, 40),
    SymbolEntry("dag", "DAG", "small_molecule",
                "Diacylglycerol. Glycerol head + 2 fatty acid tails.",
                50, 40),
    # Modifications
    SymbolEntry("p_badge", "Phosphorylation badge", "modification",
                "Small red 'P' badge. Place near the modified residue or protein.",
                24, 24),
    SymbolEntry("ub_badge", "Ubiquitin badge", "modification",
                "Small purple 'Ub' badge.",
                28, 24),
    SymbolEntry("ac_badge", "Acetylation badge", "modification",
                "Small green 'Ac' badge.",
                28, 24),
    # Organelles
    SymbolEntry("nucleus", "Nucleus", "organelle",
                "Cell nucleus with double membrane and nuclear pores.",
                200, 150),
    SymbolEntry("mitochondrion", "Mitochondrion", "organelle",
                "Mitochondrion with cristae.",
                150, 80),
    SymbolEntry("er_compartment", "Endoplasmic reticulum", "organelle",
                "ER cisterna / sheet. Use for IP₃R-bearing intracellular Ca²⁺ store.",
                200, 120),
    SymbolEntry("golgi", "Golgi apparatus", "organelle",
                "Stacked Golgi cisternae.",
                120, 80),
    SymbolEntry("autophagosome", "Autophagosome", "organelle",
                "Double-membraned vesicle (TWO concentric circles, the "
                "defining feature) engulfing a cellular cargo (drawn here "
                "as a damaged mitochondrion fragment). Use for autophagy / "
                "mitophagy figures. Place in cytoplasm adjacent to a "
                "lysosome to depict autophagosome-lysosome fusion → "
                "autolysosome. Distinct from `endocytosis` (single membrane, "
                "extracellular cargo) and from `lysosome` (single membrane, "
                "acidic enzymes).",
                80, 80),
    SymbolEntry("lysosome", "Lysosome", "organelle",
                "Single-membrane acidic vesicle (purple palette signals "
                "low pH) with scattered hydrolase enzymes inside (dark "
                "dots). Use for autophagy fusion partners, endocytic "
                "degradation, viral entry, lysosomal storage disease "
                "figures. Pair with `autophagosome` for autophagy panels.",
                60, 60),
    # Structural
    SymbolEntry("lipid_bilayer", "Lipid bilayer", "structural",
                "Tileable membrane fragment. Use multiple <use> with adjacent x-positions to build a long membrane.",
                100, 24),
    # General schematic — useful for abstract pipelines, workflows, frameworks
    SymbolEntry("microscope", "Microscope", "general",
                "Research / discovery / basic-science stage. Place inside Discovery / Research stage boxes.",
                40, 60),
    SymbolEntry("lab_flask", "Lab flask", "general",
                "Lab work / preclinical / wet-bench stage. Erlenmeyer flask with liquid.",
                40, 50),
    SymbolEntry("pill_capsule", "Pill / drug capsule", "general",
                "Pharmaceutical / drug / therapeutic. Capsule shape, two-tone.",
                60, 25),
    SymbolEntry("patient_silhouette", "Patient / human subject", "general",
                "Clinical trial / human-subject / patient stage. Head + shoulders silhouette.",
                40, 55),
    SymbolEntry("document_stamp", "Approved document", "general",
                "Regulatory approval / FDA / paperwork stage. Document with red checkmark stamp.",
                45, 50),
    SymbolEntry("chart_graph", "Chart / analytics", "general",
                "Analytics / surveillance / data-monitoring stage. Bar chart with trend line.",
                50, 40),
    SymbolEntry("milestone_marker", "Milestone flag", "general",
                "Timeline waypoint / milestone. Orange flag on pole.",
                30, 40),
    SymbolEntry("gear", "Gear / process", "general",
                "Process / mechanism / operations. Mechanical gear.",
                40, 40),
    SymbolEntry("clock", "Clock / time", "general",
                "Time / duration / scheduling.",
                40, 40),
    SymbolEntry("magnifying_glass", "Magnifying glass / analysis", "general",
                "Analysis / inspection / discovery. Lens with handle.",
                40, 40),
    # Cell-division / genetics — detail-rich, third-party.
    # Bigger than our hand-written symbols, but they collapse entire diagrams
    # into a single <use/>. Lazy-injected — only loaded when actually referenced.
    # See ATTRIBUTIONS.md for the licensing roll-up.
    SymbolEntry("bioicons_mitosis", "Mitosis cycle diagram", "cell_division",
                "Full mitosis cycle (prophase → telophase) as one composite icon. "
                "Drop this in to depict cell division stages without drawing each cell. "
                "Servier line-art aesthetic.",
                380, 440),
    SymbolEntry("bioicons_meiosis", "Meiosis cycle diagram", "cell_division",
                "Full meiosis cycle (8 stages incl. both divisions) as one composite icon. "
                "Use for figures comparing meiosis vs mitosis, or showing germ-cell formation. "
                "Wider aspect than mitosis (8:5 vs 4:5). Servier line-art aesthetic.",
                574, 347),
    SymbolEntry("bioicons_chromosome", "Chromosome (labelless)", "cell_division",
                "X-shaped condensed chromosome with sister chromatids. "
                "No baked-in labels — overlay your own <text> for allele/gene names. "
                "Servier line-art aesthetic.",
                100, 130),
    # Early embryo development — Xi Chen, CC0. Photorealistic-leaning style:
    # white outer cytoplasm + blue zona pellucida + mauve nuclei. Different
    # aesthetic from Servier; use as a self-contained panel rather than mixing.
    SymbolEntry("bioicons_zygote", "Zygote (1-cell embryo)", "cell_division",
                "Fertilised egg / 1-cell embryo. Two visible pronuclei (paternal + maternal) "
                "inside zona pellucida + polar body. Use for fertilisation figures.",
                64, 64),
    SymbolEntry("bioicons_embryo_2cell", "2-cell embryo", "cell_division",
                "2-cell stage embryo (first cleavage division complete). "
                "Use in cleavage / early-development figures alongside zygote.",
                64, 64),
    SymbolEntry("bioicons_sperm", "Sperm cell", "cell_division",
                "Sperm with elongated tail (~5.5:1 aspect, horizontal). "
                "Use in fertilisation figures — place pointing toward an "
                "egg / zygote. Detailed Xi-Chen photorealistic style.",
                167, 31),
    SymbolEntry("bioicons_embryo_morula", "Morula (16-cell embryo)", "cell_division",
                "Morula stage embryo — a cluster of cells (~16-32) packed "
                "together. Use after 2-cell + 4-cell + 8-cell in a cleavage "
                "sequence; precedes blastocyst.",
                64, 64),
    SymbolEntry("bioicons_embryo_blastocyst", "Blastocyst (early)",
                "cell_division",
                "Early blastocyst — embryo with a fluid-filled cavity "
                "(blastocoel) and inner cell mass. Use as the final panel "
                "of a fertilisation-to-implantation figure or as the "
                "starting point for ES-cell derivation diagrams.",
                64, 64),
    # ECM / matrix proteins — hand-written (bioicons.com has only collagen
    # in this domain; the others below fill the gap).
    SymbolEntry("basement_membrane", "Basement membrane (sheet)", "ecm",
                "Two-layer peach band — lamina lucida (top) + lamina densa "
                "(bottom). Use as a horizontal sheet UNDER epithelial cells "
                "(plant a horizontal band ~20-30 px below the cell membrane). "
                "Pair with hemidesmosome for cell anchoring, or with laminin/"
                "collagen IV labels for composition figures.",
                200, 28),
    SymbolEntry("hemidesmosome", "Hemidesmosome", "ecm",
                "Cell ↔ basement-membrane junction. Shows intermediate "
                "filaments anchored in a cytoplasmic plaque, integrin α6β4 "
                "transmembrane bars, and basement membrane below. Use INSTEAD "
                "of desmosome when depicting epithelial cell attachment to "
                "the BM (vs cell-cell adhesion). Completes the junction "
                "quartet: tight_junction (barrier), gap_junction (communication), "
                "desmosome (cell-cell mechanical), hemidesmosome (cell-BM).",
                100, 92),
    SymbolEntry("fibronectin", "Fibronectin (V-dimer)", "ecm",
                "V-shaped fibronectin dimer with FN-domain beads along each "
                "arm and an RGD loop at the junction (the integrin-binding "
                "motif). Use in ECM panels alongside collagen; commonly "
                "shown bridging integrin to collagen / fibrillar matrix.",
                180, 70),
    SymbolEntry("laminin", "Laminin (cross)", "ecm",
                "Cross-shaped laminin with 3 short arms + 1 long arm, each "
                "terminating in a globular head and lined with domain beads. "
                "Use in basement-membrane figures; the long arm typically "
                "engages integrin / dystroglycan on the cell side.",
                120, 120),
    SymbolEntry("proteoglycan", "Proteoglycan (bottle-brush)", "ecm",
                "Bottle-brush structure — core protein (pink horizontal line) "
                "with many GAG side-chains (vertical bristles with bead-chains). "
                "Use for figures depicting tissue hydration, growth-factor "
                "sequestration in the matrix, or aggrecan/syndecan biology.",
                200, 90),
    # ECM / tissue (third-party, Servier line-art).
    SymbolEntry("bioicons_collagen", "Collagen fibre (horizontal)", "ecm",
                "Twisted triple-helix collagen fibre rendered as a long "
                "horizontal braid (~8:1 aspect). Use for ECM panels showing "
                "fibrous matrix between cells; tile horizontally for a longer "
                "fibre or stack vertically for parallel fibres.",
                528, 67),
    SymbolEntry("bioicons_collagen_3d", "Collagen fibre (3D, upright)", "ecm",
                "Triple-helix collagen rendered as an upright 3D braid "
                "(~1:4 aspect). Use for close-ups depicting collagen "
                "structure or when a vertical orientation fits the layout.",
                120, 487),
    SymbolEntry("bioicons_fibroblast", "Fibroblast", "ecm",
                "Stellate fibroblast cell — the dominant ECM-producing cell "
                "type. Use in figures showing matrix deposition, wound "
                "healing, or fibrosis. Single-cell icon, ~3:1 aspect.",
                363, 122),
    SymbolEntry("bioicons_tight_junction", "Tight junction", "ecm",
                "Two adjacent epithelial cells bound by tight-junction strands "
                "(claudin/occludin protein lines shown as blue dots). Use for "
                "barrier-function figures, paracellular transport, polarity.",
                316, 539),
    SymbolEntry("bioicons_desmosome", "Spot desmosome", "ecm",
                "Three adjacent cells with desmosome attachments shown as "
                "intermediate-filament anchors. Use for cell-cell adhesion "
                "figures (skin, cardiac tissue).",
                708, 503),
    SymbolEntry("bioicons_gap_junction", "Gap junction", "ecm",
                "Two adjacent cell membranes with connexon channels (green "
                "hexagonal proteins) spanning between them. Use for cell-"
                "cell communication figures, electrical coupling, small-"
                "molecule exchange, cardiac syncytium. Complements "
                "tight_junction (barrier) and desmosome (mechanical "
                "adhesion) in the junction trio.",
                324, 536),
    SymbolEntry("bioicons_endocytosis",
                "Endocytosis / phagocytosis (vesicle internalisation)",
                "trafficking",
                "Cell-membrane closeup showing extracellular cargo (orange "
                "particles) being engulfed into a budding vesicle, with an "
                "arrow indicating internalisation. Use for ANY vesicle "
                "internalisation pathway: receptor-mediated endocytosis, "
                "phagocytosis (macrophage engulfing bacteria), pinocytosis, "
                "viral entry, receptor recycling. The 'cargo' particles can "
                "represent ligands, viral particles, or whole bacteria.",
                238, 222),
    SymbolEntry("bioicons_ribosome", "Ribosome translating mRNA", "trafficking",
                "Pink ribosome (large + small subunit labelled) with mRNA "
                "strand threading through (colored codon barcode). Use for "
                "translation / protein synthesis figures, polysome cascades, "
                "co-translational translocation at the ER.",
                642, 426),
    SymbolEntry("bioicons_cancer_cell", "Cancer cell (single)", "oncology",
                "Single cancer cell with irregular orange cytoplasm and a "
                "blue nucleus showing chromatin. Use INSTEAD of `generic_protein` "
                "labelled 'Tumor cell' in invasion / metastasis figures. "
                "Default ~140×155.",
                143, 156),
    SymbolEntry("bioicons_tumor", "Tumor mass", "oncology",
                "Tumor mass cross-section — yellow/cream tissue with a "
                "darker pink/red outer rim. Use for whole-tumor figures, "
                "tumor microenvironment context, or as a target object for "
                "treatment-pathway figures.",
                97, 95),
    # Immunology (bundled — Servier Blood_Immunology).
    SymbolEntry("bioicons_antibody", "Antibody (Y-shape)", "immunology",
                "Classic grey Y-shaped antibody / immunoglobulin (IgG-like). "
                "Use for immune-response figures: antigen binding, opsonisation, "
                "neutralisation, antibody-mediated effector functions. Add a "
                "<text> for isotype (IgG, IgM, IgA, IgE, IgD) when relevant.",
                70, 83),
    SymbolEntry("bioicons_t_lymphocyte", "T lymphocyte", "immunology",
                "T cell — blue/pink round lymphocyte with prominent nucleus. "
                "Use for adaptive-immunity figures (helper T cells, cytotoxic "
                "T cells, regulatory T cells). Visually similar to "
                "`bioicons_b_lymphocyte` — distinguish by <text> label "
                "(CD4+, CD8+, Th1, etc.).",
                124, 127),
    SymbolEntry("bioicons_b_lymphocyte", "B lymphocyte", "immunology",
                "B cell — round lymphocyte (visually similar to T cell — real "
                "biology has them indistinguishable under standard microscopy). "
                "Use for humoral-immunity figures, plasma-cell differentiation, "
                "antibody production. Distinguish from T cell by adjacent "
                "<text> label.",
                122, 118),
    SymbolEntry("bioicons_macrophage", "Macrophage", "immunology",
                "Stellate macrophage / antigen-presenting cell with "
                "characteristic pseudopodial extensions. Use for innate-immunity, "
                "phagocytosis, antigen presentation (pair with mhc_complex on "
                "its surface and a facing t_lymphocyte for the immune-synapse "
                "picture). Green palette signals 'immune cell' role.",
                150, 162),
    # Cytoskeleton (third-party, Servier line-art).
    SymbolEntry("bioicons_microtubule", "Microtubule lattice", "cytoskeleton",
                "Blue tubulin lattice showing the 13-protofilament structure "
                "of a microtubule (~3:1 aspect, horizontal). Use for intra-"
                "cellular transport figures, mitotic spindle close-ups, "
                "ciliary axoneme schematics.",
                181, 70),
    SymbolEntry("bioicons_actin_filament", "Actin filament", "cytoskeleton",
                "Green double-helix actin filament (~8:1 aspect, horizontal). "
                "Use for cytoskeleton figures, contractile machinery, focal "
                "adhesion / integrin-linked actin context, cell migration.",
                197, 25),
    # Per-stage mitosis icons — thin viewBox-crops of bioicons_mitosis.
    # These let the LLM place ONE icon per stage with its label adjacent,
    # solving the label-alignment problem of the composite icon (see
    # docs/progress/260512_bioicons_pilot.md H29). Sized to fit the
    # original aspect ratio of each cropped region.
    SymbolEntry("bioicons_mitosis_interphase", "Mitosis: interphase",
                "cell_cycle_stage",
                "Single oval cell with chromatin condensed into a tight cluster, "
                "nuclear envelope intact. Cropped from bioicons_mitosis composite. "
                "Use as the FIRST panel in a multi-stage cell-cycle figure.",
                145, 105),
    SymbolEntry("bioicons_mitosis_prophase", "Mitosis: prophase",
                "cell_cycle_stage",
                "Single oval cell with distinct condensed chromosomes scattered "
                "inside, nuclear envelope dissolved. Use after interphase in a "
                "stage-by-stage cell-cycle figure.",
                160, 110),
    SymbolEntry("bioicons_mitosis_prometaphase", "Mitosis: prometaphase",
                "cell_cycle_stage",
                "Single oval cell, transitional state between prophase and "
                "metaphase; chromosomes still scattered but moving toward the "
                "centre. Use as the third panel.",
                165, 110),
    SymbolEntry("bioicons_mitosis_metaphase", "Mitosis: metaphase",
                "cell_cycle_stage",
                "Single oval cell showing full bipolar spindle with chromosomes "
                "aligned at the metaphase plate. The most recognisable mitosis "
                "stage — use as the centre panel of a 5-stage figure.",
                160, 105),
    SymbolEntry("bioicons_mitosis_anaphase", "Mitosis: anaphase",
                "cell_cycle_stage",
                "Single oval cell — chromosomes scattered as sister chromatids "
                "are pulled to opposite poles. Use between metaphase and "
                "telophase in a 6-stage figure.",
                125, 95),
    SymbolEntry("bioicons_mitosis_telophase", "Mitosis: telophase / cytokinesis",
                "cell_cycle_stage",
                "Figure-8 split cell — cleavage furrow nearly complete, "
                "chromosomes pulled to opposite poles, two daughter cells "
                "almost separated. Use as the FINAL panel.",
                175, 110),
    # Meiosis stage crops (parent composite: bioicons_meiosis). Same
    # viewBox-cropping pattern as the mitosis sub-symbols.
    SymbolEntry("bioicons_meiosis_prophase_i", "Meiosis I: prophase",
                "cell_cycle_stage",
                "Big oval with homologous chromosomes paired (tetrads). "
                "Crossover-style chiasmata visible between homologs. Use as "
                "the FIRST panel of a meiosis figure.",
                210, 210),
    SymbolEntry("bioicons_meiosis_metaphase_i", "Meiosis I: metaphase",
                "cell_cycle_stage",
                "Big oval with tetrads (paired homologs) aligned at the "
                "metaphase plate. Distinct from mitosis_metaphase which "
                "aligns single chromosomes, not homolog pairs.",
                175, 210),
    SymbolEntry("bioicons_meiosis_anaphase_i", "Meiosis I: anaphase",
                "cell_cycle_stage",
                "Medium oval — homologs pulled to opposite poles. Sister "
                "chromatids remain paired (unlike mitosis anaphase, where "
                "sisters split). One chromosome per pole as X-shape.",
                135, 125),
    SymbolEntry("bioicons_meiosis_telophase_i", "Meiosis I: telophase",
                "cell_cycle_stage",
                "Medium oval — late Meiosis I; nuclear envelopes reforming "
                "around 2 cells, each with half the original chromosome "
                "complement (sister chromatids still paired).",
                135, 130),
    SymbolEntry("bioicons_meiosis_prophase_ii", "Meiosis II: prophase",
                "cell_cycle_stage",
                "Small oval — start of Meiosis II; sister chromatids "
                "condensed and paired. Use after Meiosis I telophase in an "
                "8-stage figure.",
                95, 85),
    SymbolEntry("bioicons_meiosis_metaphase_ii", "Meiosis II: metaphase",
                "cell_cycle_stage",
                "Small oval — sister chromatids aligned at the metaphase "
                "plate (single chromosomes, NOT tetrads as in Meiosis I).",
                95, 80),
    SymbolEntry("bioicons_meiosis_anaphase_ii", "Meiosis II: anaphase",
                "cell_cycle_stage",
                "Small oval — sister chromatids separate and move to "
                "opposite poles. Each pole now has a single chromatid.",
                95, 75),
    SymbolEntry("bioicons_meiosis_telophase_ii", "Meiosis II: telophase / gamete",
                "cell_cycle_stage",
                "Small oval — single haploid daughter cell (one chromatid "
                "per chromosome). Meiosis II produces 4 such cells from one "
                "original; use as the FINAL panel.",
                95, 75),
]


def build_defs_block() -> str:
    """Return a `<defs>...</defs>` block containing every symbol.

    Used by tests and by callers that explicitly want the full library.
    Path A's runtime uses `build_defs_block_for` (lazy) instead so the
    output SVG only carries the symbols the LLM actually referenced.
    """
    return "<defs>\n" + "\n".join(SYMBOLS.values()) + "\n</defs>"


def build_defs_block_for(symbol_ids: list[str] | set[str] | tuple[str, ...]) -> str:
    """Return a `<defs>...</defs>` block containing only the requested symbols.

    Unknown ids are silently skipped — the SVG validator catches unresolved
    `<use href="#...">` references, so a missing symbol surfaces as a real
    error rather than a corrupt-but-renders artefact.

    Returns the empty string when no requested ids match the library, so
    callers can splice unconditionally without producing an empty
    `<defs></defs>` wrapper.
    """
    needed = [SYMBOLS[sid] for sid in symbol_ids if sid in SYMBOLS]
    if not needed:
        return ""
    return "<defs>\n" + "\n".join(needed) + "\n</defs>"


def build_catalog_for_prompt() -> str:
    """Return a markdown-bullet catalog suitable for inclusion in the system prompt."""
    by_cat: dict[str, list[SymbolEntry]] = {}
    for entry in CATALOG:
        by_cat.setdefault(entry.category, []).append(entry)

    order = [
        "receptor", "enzyme", "signaling", "small_molecule", "modification",
        "organelle", "structural", "general", "cell_division",
        "cell_cycle_stage", "ecm", "cytoskeleton", "trafficking", "oncology",
        "immunology",
    ]
    titles = {
        "receptor": "Receptors / membrane proteins",
        "enzyme": "Cytosolic enzymes / proteins",
        "signaling": (
            "Signaling-pathway extensions (transcription factors, scaffolds, "
            "small GTPases)"
        ),
        "small_molecule": "Ions and small molecules",
        "modification": "Post-translational modifications",
        "organelle": "Organelles",
        "structural": "Structural elements",
        "general": "General schematic (workflows, pipelines, timelines)",
        "cell_division": "Cell division & genetics (third-party, detail-rich)",
        "cell_cycle_stage": (
            "Individual mitosis-stage icons (use for stage-by-stage labelled "
            "figures; place each next to its name label)"
        ),
        "ecm": "Extracellular matrix / tissue (third-party, detail-rich)",
        "cytoskeleton": (
            "Cytoskeleton filaments (third-party, detail-rich) — use for "
            "intracellular transport / structural figures and to bridge "
            "integrin to actin in ECM-cell signaling figures"
        ),
        "trafficking": (
            "Vesicle trafficking & translation (third-party, detail-rich)"
        ),
        "oncology": (
            "Cancer cells & tumor masses (third-party, detail-rich) — "
            "use INSTEAD of `generic_protein` labelled 'Tumor cell'"
        ),
        "immunology": (
            "Immune cells & antibodies (third-party, detail-rich) — "
            "T cells, B cells, macrophages, antibodies. Pair with "
            "`mhc_complex` (in receptors) for antigen-presentation figures"
        ),
    }
    lines: list[str] = []
    for cat in order:
        if cat not in by_cat:
            continue
        lines.append(f"\n**{titles[cat]}**")
        for e in by_cat[cat]:
            lines.append(
                f"- `{e.id}` ({e.name}, {e.default_w}×{e.default_h}): {e.use_when}"
            )
    return "\n".join(lines).strip()
