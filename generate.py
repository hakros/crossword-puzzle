import sys

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
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
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
        domainsCopy = self.domains.copy()

        for variable in domainsCopy:
            words = domainsCopy[variable].copy()

            for word in words:
                if (variable.length == len(word)):
                    continue

                self.domains[variable].remove(word)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        xWords: set = self.domains[x].copy()
        yWords: set = self.domains[y]

        hasMods = False

        if (x,y) not in self.crossword.overlaps:
            return hasMods

        overlap = self.crossword.overlaps[x, y]

        if overlap is None:
            return hasMods

        for xWord in xWords:
            consistent = False

            for yWord in yWords:
                # Check if the letter in xWord is the same as letter in yWord
                # for which the letter in xWord is in the same position as the letter in yWord
                if (xWord[overlap[0]] == yWord[overlap[1]]):
                    consistent = True
                    break

            if not consistent:
                self.domains[x].remove(xWord)
                hasMods = True

        return hasMods
    
    def initArcs(self) -> list:
        """
        Make the initial list of arcs
        """

        xAxis = self.domains.copy()
        yAxis = self.domains.copy()
        overlaps = self.crossword.overlaps

        arcs: list = []
        for x in xAxis:
            for y in yAxis:
                key = (x, y)
                hasOverlap = key in overlaps and overlaps[key] is not None

                if x == y or not hasOverlap:
                    continue

                arcs.append((x, y))

        return arcs

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """

        if arcs is None:
            # Make an initial list of arcs
            # Where each arcs is a tuple of variable x and a different variable y
            arcs = self.initArcs()

        # Make a queue
        queue = arcs.copy()

        # We have 1 binary constraints
        # letter of xWord in position i, should be consistent with letter of yWord in position j
        # positions of overlaps are stored in self.crossword.overlaps
        while len(queue) > 0:
            arc = queue.pop(0)

            if len(self.domains[arc[0]]) == 0:
                return False

            if self.revise(arc[0], arc[1]):
                self.addRelatedArcsToQueue(arc[0], queue, arcs)

        return True
    
    def addRelatedArcsToQueue(self, modifiedDomain, queue: list, arcs: list):
        """
        Adds all arcs related to the modified domain into the queue
        """
        for arc in arcs:
            if arc[1] != modifiedDomain:
                continue

            queue.append(arc)

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for variable in self.domains:
            if variable not in assignment or len(assignment[variable]) <= 0 or type(assignment[variable]) != str:
                return False

        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        valuesAssigned: list = []
        for variable in assignment:
            value = assignment[variable]

            if value in valuesAssigned or len(value) != variable.length:
                return False
            
            neighbors = self.crossword.neighbors(variable)
            for neighbor in neighbors:
                overlap = self.crossword.overlaps[variable, neighbor]

                # If neighbor is not yet in assignment, this technically satisfies the condition that there is no conflict
                # There can't be any conflict if there ain't nothing to compare
                if neighbor not in assignment:
                    continue

                neighborValue = assignment[neighbor]

                if value[overlap[0]] != neighborValue[overlap[1]]:
                    return False

            valuesAssigned.append(value)

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """

        values = self.domains[var]
        neighbors = self.crossword.neighbors(var)

        ruledOutNums = []
        sortedValues = []

        for value in values:
            ruledOutNum = 0

            for neighbor in neighbors:
                if neighbor in assignment:
                    continue

                words = self.domains[neighbor]
                overlap = self.crossword.overlaps[(var, neighbor)]

                if overlap is None:
                    continue

                for word in words:
                    if value[overlap[0]] != word[overlap[1]]:
                        ruledOutNum += 1

            ruledOutNums.append((ruledOutNum, value))

        ruledOutNums.sort()

        for keyValuePair in ruledOutNums:
            sortedValues.append(keyValuePair[1])

        return sortedValues

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """

        varToReturn = None
        for variable in self.domains:
            if variable in assignment:
                continue

            if varToReturn is None:
                varToReturn = variable
                continue

            values = self.domains[variable]
            values2 = self.domains[varToReturn]

            if len(values) < len(values2) or len(values) == len(self.domains[varToReturn]):
                varToReturn = variable
                continue

        return varToReturn
    
    def makeArcs(self, assignment):
        """
        Make a list of arcs
        The list should not contain variables that already exists in assignments
        """

        xAxis = self.domains.copy()
        yAxis = self.domains.copy()
        overlaps = self.crossword.overlaps

        arcs: list = []
        for x in xAxis:
            if x in assignment:
                continue

            for y in yAxis:
                if y in assignment:
                    continue

                key = (x, y)
                hasOverlap = key in overlaps and overlaps[key] is not None

                if x == y or not hasOverlap:
                    continue

                arcs.append((x, y))

        return arcs

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        variable = self.select_unassigned_variable(assignment)
        while variable is not None:
            words = self.domains[variable]

            # Variable has no assigned value and there is no possible value to assign to it
            if len(words) == 0:
                return None

            sortedValues = self.order_domain_values(variable, assignment)
            word = sortedValues[0]

            assignment[variable] = word

            arcs = self.makeArcs(assignment)

            if not self.consistent(assignment):
                self.domains[variable].remove(word)
                self.enforce_node_consistency()
                del assignment[variable]

            if len(arcs) > 0 and self.ac3(arcs) is False:
                del assignment[variable]

            if (self.assignment_complete(assignment)):
                return assignment

            variable = self.select_unassigned_variable(assignment)

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
