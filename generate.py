import sys
from random import sample
from copy import deepcopy

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        # Remove a word from a variable's domain
        # if word's length != variable's length
        removeWords = list()
        for variable in self.domains.keys():
            for word in self.domains[variable]:
                if len(word) != variable.length:
                    removeWords.append((variable, word))

        for variable, word in removeWords:
            self.domains[variable].remove(word)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        # x's domain must only contain those words that satisfy the overlaps with y
        removeWords = list()
        revisionMade = False
        for wordX in self.domains[x]:
            palFound = False
            for wordY in self.domains[y]:
                overlap = self.crossword.overlaps[x, y]
                if overlap is None:
                    continue
                # If the letters match
                if wordX[overlap[0]] == wordY[overlap[1]] and wordX != wordY:
                    palFound = True
                    break
            if not palFound:
                # Remove the word from x's domain
                removeWords.append((x, wordX))
                revisionMade = True

        for x, wordX in removeWords:
            self.domains[x].remove(wordX)

        return revisionMade

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None:
            arcs = list()
            # Use all arcs in the problem
            for overlapTuple, overlap in self.crossword.overlaps.items():
                # Overlap is all the arcs in the problem
                if overlap is not None:
                    arcs.append(overlapTuple)
        while len(arcs) > 0:
            # Revise the arc (x, y)
            # The arcs is a queue, so dequeue an arc
            arc = arcs[0]
            arcs.remove(arc)
            # If the revision is made, add all arcs of form (z, x) to arcs
            if self.revise(x=arc[0], y=arc[1]):
                # Add all neighbors of x in the form of (z, x)
                for neighbor in self.crossword.neighbors(arc[0]):
                    # Adding a neighbor to the queue
                    arcs.append((neighbor, arc[0]))

        # Check if domains are empty
        for domain in self.domains.values():
            if domain is None or len(domain) == 0:
                return False

        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for variable in self.crossword.variables:
            # If a variable isn't assigned a value, problem hasn't been solved yet
            if variable not in assignment.keys():
                return False

        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # Checking that all words are unique
        for variableA, wordA in assignment.items():
            for variableB, wordB in assignment.items():
                if variableA == variableB:
                    continue
                if wordA == wordB:
                    return False

        # Checking that the words are of right length
        for variable, word in assignment.items():
            if word is None:
                continue
            if len(word) != variable.length:
                return False

        # Checking for conflicts
        for variableA, wordA in assignment.items():
            if wordA is None:
                continue
            for variableB, wordB in assignment.items():
                if wordB is None or variableA == variableB:
                    continue
                overlap = self.crossword.overlaps[variableA, variableB]
                if overlap is None:
                    continue
                # If the letters at overlap don't match, not consistent
                if wordA[overlap[0]] != wordB[overlap[1]]:
                    return False

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """

        return list(self.domains[var])

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        unassignedVariables = set(
            self.crossword.variables) - set(assignment.keys())  # Test
        variable = sample(unassignedVariables, 1)[0]
        return variable

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        # The puzzle is solved
        if self.assignment_complete(assignment):
            return assignment

        var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(var, assignment):
            assignmentCopy = deepcopy(assignment)
            assignmentCopy[var] = value
            if self.consistent(assignmentCopy):
                assignment[var] = value
                result = self.backtrack(assignment)
                if result is not None:
                    return result
                assignment.pop(var)
        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
