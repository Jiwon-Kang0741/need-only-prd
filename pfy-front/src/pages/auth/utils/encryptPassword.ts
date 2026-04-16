import forge from 'node-forge';

/**
 * 서버에서 받은 공개키(Base64 DER)를 사용해 비밀번호를 암호화
 * RSA-OAEP + SHA-256
 */

export async function encryptPassword(
  password: string,
  fetchRsaPublic: () => Promise<string>
) {
  // 서버에서 Base64 Public Key 가져오기
  const res = await fetchRsaPublic();

  // Base64 -> binary -> ASN.1 -> PublicKey 객체
  const der = forge.util.decode64(res);
  const asn1 = forge.asn1.fromDer(der);
  const publicKey = forge.pki.publicKeyFromAsn1(asn1);

  // RSA-OAEP + SHA-256 암호화
  const encrypted = publicKey.encrypt(password, 'RSA-OAEP', {
    md: forge.md.sha256.create(),
    mgf1: { md: forge.md.sha256.create() },
  });

  // Base64 인코딩 후 반환
  return forge.util.encode64(encrypted, false);
}
