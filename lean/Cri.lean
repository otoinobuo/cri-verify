/-!
# CRI references (draft-ietf-core-href-30) versus RFC 3986 reference resolution

Segment-level model of
* Section 5.3 (reference resolution) for relative CRI references in discard form,
* Section 6.1 (conversion of a CRI reference to a URI reference): the text of draft -30 and a proposed fix,
* RFC 3986 Sections 5.2.2-5.2.4 (merge, remove_dot_segments) for a base URI that has an authority.

A path segment is abstracted to what the algorithms inspect: the dot segments "." and "..", the empty
segment "", and any other segment (identified by a number) together with whether it contains a colon.
The Python model (model/seglevel.py) checks this segment-level rendering of RFC 3986 against the literal
string algorithm.

Checked with Lean 4.33.1, core only (no Mathlib):
  ~/.elan/toolchains/leanprover--lean4---v4.33.1/bin/lean Cri.lean
-/

inductive Seg where
  | dot | dotdot | empty
  | other (id : Nat) (colon : Bool)
deriving DecidableEq, Repr

def Seg.hasColon : Seg → Bool
  | .other _ c => c
  | _ => false

/-- A base CRI with an authority (host). Its fragment is absent (RFC 3986, Section 5.1). -/
structure Base where
  path  : List Seg
  query : List Nat
deriving DecidableEq, Repr

inductive Discard where
  | all            -- the CBOR value `true`
  | n (k : Nat)    -- an unsigned integer
deriving DecidableEq, Repr

/-- A relative CRI reference in discard form (Section 5.1, Figure 2). -/
structure CRef where
  discard  : Discard
  path     : Option (List Seg)
  query    : Option (List Nat)
  fragment : Option Nat
deriving DecidableEq, Repr

/-- The local part (path, query, fragment) of a resolved CRI. -/
structure Target where
  path     : List Seg
  query    : List Nat
  fragment : Option Nat
deriving DecidableEq, Repr

/-! ## Section 5.3, steps 3-5, for the discard form -/

/-- "remove as many elements from the end of the path array" -/
def removeLast (k : Nat) (l : List Seg) : List Seg := l.take (l.length - k)

def resolveCRI (b : Base) (r : CRef) : Target :=
  let s3 : List Seg × List Nat :=                                  -- step 3
    match r.discard with
    | .all  => ([], [])
    | .n k  => (removeLast k b.path, if k = 0 then b.query else [])
  let s4 : List Seg × List Nat :=                                  -- step 4
    match r.path with
    | some p => (s3.1 ++ p, [])
    | none   => s3
  { path := s4.1,                                                  -- step 5
    query := (match r.query with | some q => q | none => s4.2),
    fragment := r.fragment }

/-! ## URI references at the segment level -/

/-- `segs = none` is the empty path "". For `some l`, `l` is non-empty; if not rooted, its first segment is non-empty. -/
structure URef where
  rooted   : Bool
  segs     : Option (List Seg)
  query    : Option (List Nat)
  fragment : Option Nat
deriving DecidableEq, Repr

def queryOf (r : CRef) : Option (List Nat) :=   -- "one or more query items"
  match r.query with | some q => if q = [] then none else some q | none => none

/-- Section 6.1 of draft -30 (path rule), followed by the collapse that the string form imposes: an
    unrooted path whose first segment is empty renders as "" (alone) or as the rooted path "/..." . -/
def convDraft (r : CRef) : Option URef :=
  let items := r.path.getD []
  match r.discard with
  | .all => some ⟨true, if items = [] then none else some items, queryOf r, r.fragment⟩
  | .n 0 => if r.path = none then some ⟨false, none, queryOf r, r.fragment⟩ else none
  | .n (k+1) =>
    let pre : List Seg := if k = 0 then (match items with | s :: _ => if s.hasColon then [.dot] else [] | [] => [])
                          else List.replicate k .dotdot
    match pre ++ items with
    | []            => some ⟨false, none, queryOf r, r.fragment⟩
    | .empty :: []  => some ⟨false, none, queryOf r, r.fragment⟩
    | .empty :: t   => some ⟨true, some t, queryOf r, r.fragment⟩
    | l             => some ⟨false, some l, queryOf r, r.fragment⟩

/-- Proposed fix of the Section 6.1 path rule: fail when the reference is not expressible, and protect an
    empty first segment with "./" like a first segment containing a colon. -/
def convFixed (r : CRef) : Option URef :=
  match r.discard with
  | .all => match r.path with
    | some (s :: t) => some ⟨true, some (s :: t), queryOf r, r.fragment⟩
    | _ => none
  | .n 0 => if r.path = none ∧ r.query ≠ some [] then some ⟨false, none, queryOf r, r.fragment⟩ else none
  | .n (k+1) => match r.path with
    | some (s :: t) =>
      let pre : List Seg := if k = 0 then (if s = .empty ∨ s.hasColon then [.dot] else []) else List.replicate k .dotdot
      some ⟨false, some (pre ++ s :: t), queryOf r, r.fragment⟩
    | _ => none

/-! ## RFC 3986, Sections 5.2.2-5.2.4, on segment lists (base with authority) -/

def rdsAux : List Seg → List Seg → List Seg
  | out, []        => out
  | out, s :: rest =>
    if s = .dot then (if rest = [] then out ++ [.empty] else rdsAux out rest)
    else if s = .dotdot then (if rest = [] then out.dropLast ++ [.empty] else rdsAux out.dropLast rest)
    else rdsAux (out ++ [s]) rest

/-- remove_dot_segments (Section 5.2.4) for a rooted path. -/
def rds (l : List Seg) : List Seg := rdsAux [] l

/-- merge (Section 5.2.3) when the base has an authority. -/
def merge (bp r : List Seg) : List Seg := if bp = [] then r else bp.dropLast ++ r

/-- Section 5.2.2 for a relative reference (no scheme, no authority). -/
def resolve3986 (b : Base) (u : URef) : Target :=
  match u.segs with
  | none   => ⟨b.path, u.query.getD b.query, u.fragment⟩
  | some l => ⟨if u.rooted then rds l else rds (merge b.path l), u.query.getD [], u.fragment⟩

/-! ## Counterexamples to the draft -30 conversion (all by `decide`) -/

def A : Seg := .other 0 false
def B : Seg := .other 1 false
def C : Seg := .other 2 false

def b1 : Base := ⟨[.empty], []⟩                       -- s://h/
def r1 : CRef := ⟨.n 1, none, none, none⟩              -- [1]
def u1 : URef := ⟨false, none, none, none⟩             -- the URI reference ""
example : convDraft r1 = some u1 := by decide
example : resolveCRI b1 r1 = ⟨[], [], none⟩ := by decide                 -- s://h
example : resolve3986 b1 u1 = ⟨[.empty], [], none⟩ := by decide          -- s://h/
theorem cex_discard_without_path : convDraft r1 = some u1 ∧ resolve3986 b1 u1 ≠ resolveCRI b1 r1 := by decide

def b2 : Base := ⟨[B, C], []⟩                         -- s://h/b/c
def r2 : CRef := ⟨.n 1, some [.empty, A], none, none⟩  -- [1, ["", "a"]]
def u2 : URef := ⟨true, some [A], none, none⟩          -- the URI reference "/a"
example : convDraft r2 = some u2 := by decide
example : resolveCRI b2 r2 = ⟨[B, .empty, A], [], none⟩ := by decide     -- s://h/b//a
example : resolve3986 b2 u2 = ⟨[A], [], none⟩ := by decide              -- s://h/a
theorem cex_leading_empty_segment : convDraft r2 = some u2 ∧ resolve3986 b2 u2 ≠ resolveCRI b2 r2 := by decide

def b3 : Base := ⟨[A, .empty], []⟩                    -- s://h/a/
def r3 : CRef := ⟨.n 2, some [], none, none⟩           -- [2, []]
def u3 : URef := ⟨false, some [.dotdot], none, none⟩   -- the URI reference "../"
example : convDraft r3 = some u3 := by decide
theorem cex_discard_two_without_path : convDraft r3 = some u3 ∧ resolve3986 b3 u3 ≠ resolveCRI b3 r3 := by decide
example : resolveCRI b3 r3 = ⟨[], [], none⟩ := by decide                 -- s://h
example : resolve3986 b3 u3 = ⟨[.empty], [], none⟩ := by decide          -- s://h/

def b4 : Base := ⟨[], [7]⟩                            -- s://h?q
def r4 : CRef := ⟨.n 0, none, some [], none⟩           -- [0, null, []]  (Section 2.3: not expressible)
theorem cex_discard_zero_empty_query : convDraft r4 = some u1 ∧ resolve3986 b4 u1 ≠ resolveCRI b4 r4 := by decide

/-- The fixed conversion refuses the inexpressible references and repairs the third. -/
example : convFixed r1 = none ∧ convFixed r3 = none ∧ convFixed r4 = none := by decide
example : convFixed r2 = some ⟨false, some [.dot, .empty, A], none, none⟩ := by decide   -- ".//a"
example : resolve3986 b2 ⟨false, some [.dot, .empty, A], none, none⟩ = resolveCRI b2 r2 := by decide

/-! ## Soundness of the fixed conversion for every base with an authority -/

/-- C9: CRI path segments are never "." or "..". -/
def NoDots (l : List Seg) : Prop := ∀ s ∈ l, s ≠ .dot ∧ s ≠ .dotdot

theorem noDots_cons {s : Seg} {l : List Seg} (h : NoDots (s :: l)) : (s ≠ .dot ∧ s ≠ .dotdot) ∧ NoDots l :=
  ⟨h s (List.mem_cons_self), fun x hx => h x (List.mem_cons_of_mem _ hx)⟩

theorem rdsAux_nodots (out l : List Seg) (h : NoDots l) : rdsAux out l = out ++ l := by
  induction l generalizing out with
  | nil => simp [rdsAux]
  | cons s rest ih =>
    obtain ⟨⟨h1, h2⟩, hrest⟩ := noDots_cons h
    simp only [rdsAux, h1, h2, if_false]
    rw [ih (out ++ [s]) hrest]
    simp

theorem rdsAux_prefix (out l rest : List Seg) (h : NoDots l) : rdsAux out (l ++ rest) = rdsAux (out ++ l) rest := by
  induction l generalizing out with
  | nil => simp
  | cons s t ih =>
    obtain ⟨⟨h1, h2⟩, ht⟩ := noDots_cons h
    simp only [List.cons_append, rdsAux, h1, h2, if_false]
    rw [ih (out ++ [s]) ht]
    simp

theorem replicate_append_ne_nil (k : Nat) (s : Seg) (l : List Seg) (hl : l ≠ []) : List.replicate k s ++ l ≠ [] := by
  cases k <;> simp [List.replicate, hl]

theorem take_dropLast (l : List Seg) (k : Nat) : l.dropLast.take (l.dropLast.length - k) = l.take (l.length - (k+1)) := by
  rw [List.dropLast_eq_take, List.take_take, List.length_take]
  have : min (min (l.length - 1) l.length - k) (l.length - 1) = l.length - (k+1) := by omega
  rw [this]

theorem mem_of_mem_dropLast' {x : Seg} {l : List Seg} (h : x ∈ l.dropLast) : x ∈ l := by
  rw [List.dropLast_eq_take] at h; exact List.mem_of_mem_take h

theorem rdsAux_dotdots (k : Nat) (out items : List Seg) (hi : NoDots items) (hne : items ≠ []) :
    rdsAux out (List.replicate k .dotdot ++ items) = out.take (out.length - k) ++ items := by
  induction k generalizing out with
  | zero => simp [rdsAux_nodots out items hi]
  | succ k ih =>
    have hrest := replicate_append_ne_nil k .dotdot items hne
    simp only [List.replicate, List.cons_append, rdsAux, hrest, reduceCtorEq, if_false, if_true]
    rw [ih out.dropLast, take_dropLast]

theorem rdsAux_dot (out items : List Seg) (hi : NoDots items) (hne : items ≠ []) :
    rdsAux out (.dot :: items) = out ++ items := by
  simp only [rdsAux, if_true, hne, if_false]
  exact rdsAux_nodots out items hi

/-- For a base with authority and a path without dot segments, resolving the fixed URI reference per RFC 3986
    gives exactly the CRI resolution of Section 5.3. -/
theorem convFixed_sound (b : Base) (r : CRef) (u : URef) (hb : NoDots b.path)
    (hp : ∀ p, r.path = some p → NoDots p) (hc : convFixed r = some u) :
    resolve3986 b u = resolveCRI b r := by
  obtain ⟨d, p, q, f⟩ := r
  obtain ⟨bp, bq⟩ := b
  simp only at hb hp
  cases d with
  | all =>
    cases p with
    | none => simp [convFixed] at hc
    | some p =>
      cases p with
      | nil => simp [convFixed] at hc
      | cons s t =>
        simp only [convFixed, Option.some.injEq] at hc
        subst hc
        have hnd := hp (s :: t) rfl
        simp only [resolve3986, resolveCRI, rds, rdsAux_nodots [] (s :: t) hnd, queryOf]
        cases q with
        | none => simp
        | some q => cases q <;> simp
  | n k =>
    cases k with
    | zero =>
      simp only [convFixed] at hc
      split at hc
      · rename_i hcond
        obtain ⟨hpn, hq⟩ := hcond
        subst hpn
        simp only [Option.some.injEq] at hc
        subst hc
        simp only [resolve3986, resolveCRI, removeLast, Nat.sub_zero, List.take_length, queryOf]
        cases q with
        | none => simp
        | some q =>
          cases q with
          | nil => exact absurd rfl hq
          | cons x xs => simp
      · exact absurd hc (by simp)
    | succ k =>
      cases p with
      | none => simp [convFixed] at hc
      | some p =>
        cases p with
        | nil => simp [convFixed] at hc
        | cons s t =>
          simp only [convFixed, Option.some.injEq] at hc
          subst hc
          have hnd := hp (s :: t) rfl
          have hne : (s :: t) ≠ [] := by simp
          -- the path part
          have hpath : rds (merge bp ((if k = 0 then (if s = .empty ∨ s.hasColon then [.dot] else []) else List.replicate k .dotdot) ++ s :: t))
                        = removeLast (k+1) bp ++ s :: t := by
            unfold rds merge removeLast
            split
            · rename_i hbp; subst hbp
              split
              · split
                · rw [List.singleton_append, rdsAux_dot [] (s :: t) hnd hne]; simp
                · rw [List.nil_append, rdsAux_nodots [] (s :: t) hnd]; simp
              · rw [rdsAux_dotdots k [] (s :: t) hnd hne]; simp
            · rename_i hbp
              have hbd : NoDots bp.dropLast := fun x hx => hb x (mem_of_mem_dropLast' hx)
              rw [rdsAux_prefix [] bp.dropLast _ hbd, List.nil_append]
              split
              · rename_i hk; subst hk
                split
                · rw [List.singleton_append, rdsAux_dot _ (s :: t) hnd hne, List.dropLast_eq_take]
                · rw [List.nil_append, rdsAux_nodots _ (s :: t) hnd, List.dropLast_eq_take]
              · rw [rdsAux_dotdots k _ (s :: t) hnd hne, take_dropLast]
          simp only [resolve3986, resolveCRI, queryOf, Bool.false_eq_true, if_false]
          rw [hpath]
          cases q with
          | none => simp
          | some q => cases q <;> simp

/-! ## Step 5 of Section 5.3 with a null authority (full CRI used as a reference) -/

inductive Auth where
  | host (h : Nat)   -- an authority
  | rootbased        -- CBOR null  (NOAUTH-ROOTBASED)
  | rootless         -- CBOR true  (NOAUTH-ROOTLESS)
deriving DecidableEq, Repr

/-- The authority of the buffer after steps 3 and 5 for a reference that has a scheme. Step 3 sets a
    rootless authority to null; step 5 copies "all non-null sections", so a rootbased (null) authority of
    the reference is never copied. -/
def authDraft (base ref : Auth) : Auth :=
  let a3 := if base = .rootless then .rootbased else base
  if ref = .rootbased then a3 else ref

def authFixed (_base ref : Auth) : Auth := ref   -- RFC 3986: T.authority = R.authority when R has a scheme

theorem cex_null_authority : authDraft (.host 0) .rootbased = .host 0 := by decide
theorem authFixed_matches (base ref : Auth) : authFixed base ref = ref := rfl

#print axioms cex_discard_without_path
#print axioms cex_leading_empty_segment
#print axioms cex_discard_two_without_path
#print axioms cex_discard_zero_empty_query
#print axioms convFixed_sound
#print axioms cex_null_authority
