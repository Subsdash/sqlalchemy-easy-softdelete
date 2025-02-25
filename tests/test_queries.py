"""Tests for `sqlalchemy_easy_softdelete` package."""
from typing import List

from sqlalchemy import func, select, table, text
from sqlalchemy.orm import Query
from sqlalchemy.sql import Select

from tests.model import SDChild, SDDerivedRequest, SDParent


def test_query_single_table(snapshot, seeded_session, rewriter):
    """Query with one table"""
    test_query: Query = seeded_session.query(SDChild)

    snapshot.assert_match(str(rewriter.rewrite_select(test_query.statement)))
    snapshot.assert_match(test_query.all())


def test_query_with_join(snapshot, seeded_session, rewriter):
    """Query with a simple join"""
    test_query: Query = seeded_session.query(SDChild).join(SDParent)  # noqa -- wrong typing stub in SA

    snapshot.assert_match(str(rewriter.rewrite_select(test_query.statement)))

    snapshot.assert_match(test_query.all())


def test_query_union_sdchild(snapshot, seeded_session, rewriter):
    """Two queries joined via UNION"""
    test_query: Query = seeded_session.query(SDChild).union(seeded_session.query(SDChild))

    snapshot.assert_match(str(rewriter.rewrite_select(test_query.statement)))

    snapshot.assert_match(test_query.all())


def test_query_with_union_but_union_softdelete_disabled(snapshot, seeded_session, rewriter):
    """Two queries joined via UNION but the second one has soft-delete disabled"""

    # Two SDChild .all() queries with results joined via UNION
    # the first one has soft delete applied
    # the second one has soft delete DISABLED
    # the second query is a superset of the first one, and results in
    # all objects in the DB being returned
    test_query: Query = seeded_session.query(SDChild).union(
        seeded_session.query(SDChild).execution_options(include_deleted=True)
    )

    snapshot.assert_match(str(rewriter.rewrite_select(test_query.statement)))

    all_children: List[SDChild] = seeded_session.query(SDChild).execution_options(include_deleted=True).all()

    assert sorted(test_query.all(), key=lambda x: x.id) == sorted(all_children, key=lambda x: x.id)

    snapshot.assert_match(test_query.all())


def test_ensure_aggregate_from_multiple_table_deletion_works_active_object_count(snapshot, seeded_session, rewriter):
    """Aggregate function from a query that contains a join"""
    test_query: Query = seeded_session.query(SDChild).join(SDParent).with_entities(func.count())  # noqa

    snapshot.assert_match(str(rewriter.rewrite_select(test_query.statement)))
    snapshot.assert_match(test_query.count())


def test_ensure_table_with_inheritance_works(snapshot, seeded_session, rewriter):
    test_query: Query = seeded_session.query(SDDerivedRequest)

    snapshot.assert_match(str(rewriter.rewrite_select(test_query.statement)))

    test_query_results = test_query.all()
    assert len(test_query_results) == 2
    snapshot.assert_match(test_query_results)

    all_active_and_deleted_derived_requests = (
        seeded_session.query(SDDerivedRequest).execution_options(include_deleted=True).all()
    )

    assert len(all_active_and_deleted_derived_requests) == 3
    snapshot.assert_match(all_active_and_deleted_derived_requests)


def test_query_with_text_clause_as_table(snapshot, seeded_session, rewriter):
    """We cannot parse information from a literal text table name -- return unchanged"""

    # Table as a TextClause
    test_query_text_clause: Select = select(text('id')).select_from(text("sdderivedrequest"))
    snapshot.assert_match(str(rewriter.rewrite_select(test_query_text_clause)))


def test_query_with_table_clause_as_table(snapshot, seeded_session, rewriter):
    """We cannot parse information from a literal text table name -- return unchanged"""

    # Table as a TableClause
    test_query_table_clause: Select = select(text('id')).select_from(table("sdderivedrequest"))
    snapshot.assert_match(str(rewriter.rewrite_select(test_query_table_clause)))
