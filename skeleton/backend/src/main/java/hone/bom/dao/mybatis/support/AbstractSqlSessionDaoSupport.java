package hone.bom.dao.mybatis.support;

import org.apache.ibatis.session.SqlSession;

/**
 * Hone Framework base DAO support class.
 * Provides SqlSession access for MyBatis-based DAOs.
 */
public abstract class AbstractSqlSessionDaoSupport {

    private SqlSession sqlSession;

    public void setSqlSession(SqlSession sqlSession) {
        this.sqlSession = sqlSession;
    }

    protected SqlSession getSqlSession() {
        return this.sqlSession;
    }
}
