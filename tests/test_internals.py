# pylint: disable=all
from sqlite_database.query_builder import extract_table

SQL = "CREATE TABLE tbl (row1 text not null, row2 text not null, foreign key (row2) references tbl (row1) on delete cascade on update cascade)"


def test_query_builder_table_01():
    data = extract_table(SQL)
    for col in data:
        assert col.nullable is False
        if col.name == "row2":
            assert col.raw_source == "tbl/row1"

