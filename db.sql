-- =========================================================
-- Extensions
-- =========================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
-- Opcional:
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =========================================================
-- Enums
-- =========================================================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='offering_type') THEN
    CREATE TYPE offering_type AS ENUM ('COURSE','EXAM');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='group_scope') THEN
    CREATE TYPE group_scope   AS ENUM ('ALL','ANY','NONE');  -- todas / alguna / no debe tener
  END IF;

  -- Etiqueta semántica del bloque (rótulos de la UI)
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='group_flavor') THEN
    CREATE TYPE group_flavor  AS ENUM (
      'GENERIC',
      'APPROVALS',        -- "aprobación/es entre"
      'ACTIVITIES',       -- "actividad/es entre"
      'COURSE_APPROVED',  -- "Curso aprobado de la U.C.B"
      'COURSE_ENROLLED',  -- "Inscripción a Curso de la U.C.B"
      'EXAM_APPROVED',    -- "Examen aprobado de la U.C.B"
      'EXAM_ENROLLED',    -- "Inscripción a Examen" (si aparece)
      'COURSE_CREDITED',
      'EXAM_CREDITED'
    );
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='req_condition') THEN
    CREATE TYPE req_condition AS ENUM ('APPROVED','ENROLLED','CREDITED');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='target_type') THEN
    CREATE TYPE target_type   AS ENUM ('SUBJECT','OFFERING');
  END IF;

  -- Tipo de arista normalizada para el grafo de "previas"
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='dep_kind') THEN
    CREATE TYPE dep_kind AS ENUM (
      'REQUIRES_ALL',     -- viene de un grupo ALL (obligatorio)
      'ALTERNATIVE_ANY',  -- viene de un grupo ANY (alternativa)
      'FORBIDDEN_NONE'    -- viene de un grupo NONE (incompatibilidad/antirequisito)
    );
  END IF;
END$$;

-- =========================================================
-- Programas / Planes (opcional)
-- =========================================================
CREATE TABLE IF NOT EXISTS programs (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name       TEXT NOT NULL,
  plan_year  INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- Materias canónicas
-- =========================================================
CREATE TABLE IF NOT EXISTS subjects (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  program_id  UUID REFERENCES programs(id) ON DELETE SET NULL,
  code        TEXT NOT NULL,        -- ej: CP1, 1443
  name        TEXT NOT NULL,        -- ej: Análisis Matemático I
  credits     NUMERIC(6,2),         -- si querés créditos "de la materia" (opcional)
  dept        TEXT,
  description TEXT,
  semester    INT CHECK (semester IN (1,2) OR semester IS NULL), -- sugerido en plan
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (program_id, code)
);

-- Sinónimos / variantes de código/nombre (útil para scraping)
CREATE TABLE IF NOT EXISTS subject_aliases (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  alias_code TEXT,
  alias_name TEXT,
  UNIQUE (subject_id, alias_code),
  UNIQUE (subject_id, alias_name)
);

-- =========================================================
-- Ofertas (curso / examen)
-- =========================================================
CREATE TABLE IF NOT EXISTS offerings (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  type       offering_type NOT NULL,      -- COURSE | EXAM
  term       TEXT,                        -- ej: 2025S1, 2024S2; NULL si no aplica
  section    TEXT,                        -- comisión/sección
  semester   SMALLINT CHECK (semester IN (1,2,3) OR semester IS NULL),
  -- 1 = primer semestre, 2 = segundo, 3 = ambos

  credits    NUMERIC(6,2),                -- créditos de ESTA oferta
  is_active  BOOLEAN NOT NULL DEFAULT true,

  url_source TEXT,                        -- URL origen (bedelía)
  scraped_at TIMESTAMPTZ,                 -- última fecha scraping
  html_hash  TEXT,                        -- checksum/idempotencia
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (subject_id, type, term, COALESCE(section,''))
);

-- Links asociados a la oferta (programa, moodle, github, etc.)
CREATE TABLE IF NOT EXISTS offering_links (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  offering_id UUID NOT NULL REFERENCES offerings(id) ON DELETE CASCADE,
  kind        TEXT NOT NULL,      -- 'SYLLABUS','MOODLE','PROGRAM','GITHUB', etc.
  url         TEXT NOT NULL,
  title       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- Requisitos (grupos + anidación + items)
-- =========================================================
CREATE TABLE IF NOT EXISTS requirement_groups (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  offering_id  UUID NOT NULL REFERENCES offerings(id) ON DELETE CASCADE,
  scope        group_scope NOT NULL,                 -- ALL / ANY / NONE
  flavor       group_flavor NOT NULL DEFAULT 'GENERIC',
  min_required INT,                                  -- p.ej. 1 para "1 aprobación/es entre"
  note         TEXT,
  order_index  INT NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK ((scope <> 'ANY') OR (min_required IS NULL OR min_required >= 1)),
  CHECK ((scope <> 'ALL') OR (min_required IS NULL OR min_required >= 1))
);

-- Grupo padre -> grupo hijo (para anidación)
CREATE TABLE IF NOT EXISTS requirement_group_links (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_group_id  UUID NOT NULL REFERENCES requirement_groups(id) ON DELETE CASCADE,
  child_group_id   UUID NOT NULL REFERENCES requirement_groups(id) ON DELETE CASCADE,
  order_index      INT NOT NULL DEFAULT 0,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (parent_group_id, child_group_id),
  CHECK (parent_group_id <> child_group_id)
);

-- Ítems hoja del requisito
CREATE TABLE IF NOT EXISTS requirement_items (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id           UUID NOT NULL REFERENCES requirement_groups(id) ON DELETE CASCADE,
  target_type        target_type NOT NULL,          -- SUBJECT | OFFERING
  target_subject_id  UUID REFERENCES subjects(id) ON DELETE CASCADE,
  target_offering_id UUID REFERENCES offerings(id) ON DELETE CASCADE,
  condition          req_condition NOT NULL DEFAULT 'APPROVED',
  alt_code           TEXT,                          -- fallback si no se resolvió ID
  alt_label          TEXT,                          -- texto mostrado tal cual
  order_index        INT NOT NULL DEFAULT 0,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (
    (target_type='SUBJECT'  AND target_subject_id IS NOT NULL AND target_offering_id IS NULL) OR
    (target_type='OFFERING' AND target_offering_id IS NOT NULL AND target_subject_id IS NULL)
  )
);

-- =========================================================
-- Equivalencias (opcional)
-- =========================================================
CREATE TABLE IF NOT EXISTS subject_equivalences (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_id_a UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  subject_id_b UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  kind         TEXT NOT NULL CHECK (kind IN ('FULL','PARTIAL')),
  note         TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_eq_diff CHECK (subject_id_a <> subject_id_b),
  UNIQUE (subject_id_a, subject_id_b)
);

-- =========================================================
-- Auditoría de scraping (opcional)
-- =========================================================
CREATE TABLE IF NOT EXISTS audit_sources (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  offering_id   UUID REFERENCES offerings(id) ON DELETE CASCADE,
  url           TEXT NOT NULL,
  fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  status        INT,
  html_checksum TEXT,
  parsed_ok     BOOLEAN,
  raw_snapshot  BYTEA
);

-- =========================================================
-- Dependencias materializadas (para “es previa de…”)
-- =========================================================
-- Cada fila representa una arista desde el requisito (materia/oferta origen)
-- hacia la oferta que lo exige (oferta destino), con el tipo de relación.
CREATE TABLE IF NOT EXISTS dependency_edges (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  from_type          target_type NOT NULL,                 -- SUBJECT | OFFERING
  from_subject_id    UUID REFERENCES subjects(id) ON DELETE CASCADE,
  from_offering_id   UUID REFERENCES offerings(id) ON DELETE CASCADE,

  to_offering_id     UUID NOT NULL REFERENCES offerings(id) ON DELETE CASCADE,
  to_subject_id      UUID GENERATED ALWAYS AS
                      ((SELECT subject_id FROM offerings o WHERE o.id = to_offering_id)) STORED,

  group_id           UUID NOT NULL REFERENCES requirement_groups(id) ON DELETE CASCADE,
  kind               dep_kind NOT NULL,                    -- REQUIRES_ALL / ALTERNATIVE_ANY / FORBIDDEN_NONE
  condition          req_condition NOT NULL DEFAULT 'APPROVED',

  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

  CHECK (
    (from_type='SUBJECT'  AND from_subject_id IS NOT NULL AND from_offering_id IS NULL) OR
    (from_type='OFFERING' AND from_offering_id IS NOT NULL AND from_subject_id IS NULL)
  )
);

-- Índices principales
CREATE INDEX IF NOT EXISTS idx_dep_from_subject ON dependency_edges(from_subject_id);
CREATE INDEX IF NOT EXISTS idx_dep_from_off     ON dependency_edges(from_offering_id);
CREATE INDEX IF NOT EXISTS idx_dep_to_offering  ON dependency_edges(to_offering_id);
CREATE INDEX IF NOT EXISTS idx_dep_kind         ON dependency_edges(kind);

-- =========================================================
-- Vista materializada útil: subject → subject
-- (para consultas rápidas "¿de qué materias es previa CP1?")
-- =========================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_subject_prereqs AS
SELECT
  de.from_subject_id    AS prerequisite_subject_id,
  de.to_subject_id      AS target_subject_id,
  de.kind,              -- REQUIRES_ALL / ALTERNATIVE_ANY / FORBIDDEN_NONE
  de.condition,
  de.group_id,
  rg.scope,
  rg.flavor
FROM dependency_edges de
JOIN requirement_groups rg ON rg.id = de.group_id
WHERE de.from_subject_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_mv_prereq_from ON mv_subject_prereqs(prerequisite_subject_id);
CREATE INDEX IF NOT EXISTS idx_mv_prereq_to   ON mv_subject_prereqs(target_subject_id);

-- =========================================================
-- Índices varios
-- =========================================================
CREATE INDEX IF NOT EXISTS idx_subjects_code           ON subjects(code);
CREATE INDEX IF NOT EXISTS idx_subjects_program        ON subjects(program_id);
-- CREATE INDEX IF NOT EXISTS idx_subjects_name_trgm   ON subjects USING GIN (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_offerings_subject       ON offerings(subject_id);
CREATE INDEX IF NOT EXISTS idx_offerings_type_term     ON offerings(type, term);
CREATE INDEX IF NOT EXISTS idx_offerings_active        ON offerings(is_active);
CREATE INDEX IF NOT EXISTS idx_offerings_semester      ON offerings(semester);

CREATE INDEX IF NOT EXISTS idx_req_groups_offering     ON requirement_groups(offering_id, order_index);
CREATE INDEX IF NOT EXISTS idx_req_group_links_parent  ON requirement_group_links(parent_group_id, order_index);
CREATE INDEX IF NOT EXISTS idx_req_items_group         ON requirement_items(group_id, order_index);
CREATE INDEX IF NOT EXISTS idx_req_items_target_subj   ON requirement_items(target_subject_id);
CREATE INDEX IF NOT EXISTS idx_req_items_target_off    ON requirement_items(target_offering_id);
