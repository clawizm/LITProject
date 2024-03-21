def adjust_overlap(range1, range2):
    """
    Adjusts range1 to ensure there's no overlap with range2.
    :param range1: First range tuple.
    :param range2: Second range tuple.
    :return: Adjusted range1 tuple.
    """
    start1, end1 = range1
    start2, end2 = range2

    # Check if range1 completely overlaps range2 or vice versa
    if start1 >= start2 and end1 <= end2:
        return (start1, start1)  # Or any logic to handle complete overlap
    elif start2 >= start1 and end2 <= end1:
        return (start1, start2), (end2, end1)  # Split range1 around range2

    # Partial overlap cases
    if start1 < start2 < end1 <= end2:
        return (start1, start2)  # Adjust end of range1 to start of range2
    elif start2 <= start1 < end2 < end1:
        return (end2, end1)  # Adjust start of range1 to end of range2

    # No overlap
    return range1

# Example usage
range1 = (5, 15)
range2 = (10, 20)
adjusted_range = adjust_overlap(range1, range2)
print("Adjusted Range:", adjusted_range)

