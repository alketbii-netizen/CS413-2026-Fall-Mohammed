(*
** The Eight-Queens Puzzle
** Source: "Introduction to Programming in ATS" by Hongwei Xi,
** Chapter 3 (Functions), "Example: The Eight-Queens Puzzle"
** https://ats-lang.github.io/FROZEN000/DOCUMENT/INT2PROGINATS/HTML/INT2PROGINATS-BOOK-onechunk.html
**
** A board configuration is represented as a tuple of 8 integers
** (an "int8"), where the i-th component gives the column position
** of the queen piece placed on row i.
*)

#include "share/atspre_define.hats"
#include "share/atspre_staload.hats"

#define N 8

typedef int8 = (int, int, int, int, int, int, int, int)

(* ****** ****** *)

fun print_dots (i: int): void =
  if i > 0 then (print ". "; print_dots (i-1)) else ()
// end of [print_dots]

fun print_row (i: int): void =
(
  print_dots (i); print "Q "; print_dots (N-i-1); print "\n";
) // end of [print_row]

fun print_board (bd: int8): void =
(
  print_row (bd.0); print_row (bd.1); print_row (bd.2); print_row (bd.3);
  print_row (bd.4); print_row (bd.5); print_row (bd.6); print_row (bd.7);
  print_newline ()
) // end of [print_board]

(* ****** ****** *)

fun board_get
  (bd: int8, i: int): int =
  if i = 0 then bd.0
  else if i = 1 then bd.1
  else if i = 2 then bd.2
  else if i = 3 then bd.3
  else if i = 4 then bd.4
  else if i = 5 then bd.5
  else if i = 6 then bd.6
  else if i = 7 then bd.7
  else ~1 // end of [if]
// end of [board_get]

fun board_set
  (bd: int8, i: int, j: int): int8 = let
  val (x0, x1, x2, x3, x4, x5, x6, x7) = bd
in
  if i = 0 then let
    val x0 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 1 then let
    val x1 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 2 then let
    val x2 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 3 then let
    val x3 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 4 then let
    val x4 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 5 then let
    val x5 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 6 then let
    val x6 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 7 then let
    val x7 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else bd // end of [if]
end // end of [board_set]

(* ****** ****** *)

(*
** [safety_test1] tests whether the queen piece at (i0, j0)
** and the queen piece at (i, j) do not attack each other:
** they must not share a column, and they must not share a diagonal.
*)
fun safety_test1
  (i0: int, j0: int, i: int, j: int): bool =
  j0 != j andalso abs (i0-i) != abs (j0-j)
// end of [safety_test1]

(*
** [safety_test2] tests whether placing a queen piece at row [i],
** column [j] is safe with respect to all the queen pieces already
** placed on rows 0 through [i0] of board [bd].
*)
fun safety_test2
  (i: int, j: int, bd: int8, i0: int): bool =
  if i0 >= 0 then
    safety_test1 (i0, board_get (bd, i0), i, j) andalso
    safety_test2 (i, j, bd, i0-1)
  else true // end of [if]
// end of [safety_test2]

(* ****** ****** *)

(*
** [search] performs a tail-recursive backtracking search for
** placements of queens on rows 0 through N-1.
**   bd   : the board built so far
**   i    : the row currently being worked on
**   j    : the column being tried for row [i]
**   nsol : the number of solutions found so far
** It returns the total number of solutions found.
*)
fun search
  (bd: int8, i: int, j: int, nsol: int): int =
(
if
  (j < N)
then let
  val test = safety_test2 (i, j, bd, i-1)
in
  if test then let
    val bd1 = board_set (bd, i, j)
  in
    if i+1 = N then let
      val () = print! ("Solution #", nsol+1, ":\n\n")
      val () = print_board (bd1)
    in
      search (bd, i, j+1, nsol+1)
    end (* end of [then] *) else (
      search (bd1, i+1, 0(*j*), nsol) // positioning next piece
    ) (* end of [else] *)
    // end of [if]
  end (* end of [then] *)
  else search (bd, i, j+1, nsol)
  // end of [if]
end (* end of [then] *)
else (
  if i > 0
    then search (bd, i-1, board_get (bd, i-1) + 1, nsol) else nsol
  // end of [if]
) (* end of [else] *)
//
) (* end of [search] *)

(* ****** ****** *)

implement
main0 () = let
  val bd0 = (0, 0, 0, 0, 0, 0, 0, 0): int8
  val nsol = search (bd0, 0, 0, 0)
in
  print! ("Total number of solutions = ", nsol, "\n")
end // end of [main0]
