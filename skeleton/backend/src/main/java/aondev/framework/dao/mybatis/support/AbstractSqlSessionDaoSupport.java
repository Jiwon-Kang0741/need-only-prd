package aondev.framework.dao.mybatis.support;

import java.util.List;

import org.apache.ibatis.session.SqlSession;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * Base DAO support for MyBatis. Generated DaoImpl classes extend this and call the
 * protected wrapper methods with a Mapper statement id (e.g.
 * {@code super.selectList("selectCpmsEduPgmList", param)}). The SqlSession is the
 * Spring-managed SqlSessionTemplate (mybatis-spring-boot-starter).
 */
public abstract class AbstractSqlSessionDaoSupport {

    @Autowired
    protected SqlSession sqlSession;

    protected <E> List<E> selectList(String statementId, Object parameter) {
        return this.sqlSession.selectList(statementId, parameter);
    }

    protected <E> List<E> selectList(String statementId) {
        return this.sqlSession.selectList(statementId);
    }

    protected <T> T selectOne(String statementId, Object parameter) {
        return this.sqlSession.selectOne(statementId, parameter);
    }

    protected <T> T selectOne(String statementId) {
        return this.sqlSession.selectOne(statementId);
    }

    protected int insert(String statementId, Object parameter) {
        return this.sqlSession.insert(statementId, parameter);
    }

    protected int update(String statementId, Object parameter) {
        return this.sqlSession.update(statementId, parameter);
    }

    protected int delete(String statementId, Object parameter) {
        return this.sqlSession.delete(statementId, parameter);
    }
}
